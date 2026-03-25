from __future__ import annotations
from sqlalchemy.orm import Session

from ..models.faq import FAQItem, ChatSession, ChatMessage
from ..models.store import Store
from ..services.line_service import reply_line_message, send_line_message
from ..config import settings
from ..core.logging import logger

# ユーザーが有人対応を求めるキーワード
_HUMAN_TRIGGER_WORDS = [
    "人と話したい", "スタッフ", "担当者", "オペレーター",
    "人間", "直接", "電話", "つないで", "有人",
]

# botが答えられない場合の返答
_CANNOT_ANSWER_MARKER = "CANNOT_ANSWER"


async def handle_faq_message(
    text: str,
    line_user_id: str,
    display_name: str,
    store: Store,
    reply_token: str,
    db: Session,
) -> None:
    """
    FAQボットのメインハンドラー。
    1. 有人要求キーワード検出 → エスカレーション
    2. キーワードマッチ → 即答
    3. Claude NLP → 答えられれば返答、無理なら有人エスカレーション
    """
    access_token = store.line_access_token or settings.line_channel_access_token

    # セッション取得 or 新規作成
    session = db.query(ChatSession).filter(
        ChatSession.store_id == store.id,
        ChatSession.line_user_id == line_user_id,
        ChatSession.status != "closed",
    ).first()

    if not session:
        session = ChatSession(
            store_id=store.id,
            line_user_id=line_user_id,
            display_name=display_name,
            status="bot",
        )
        db.add(session)
        db.flush()

    # ユーザーメッセージを記録
    db.add(ChatMessage(session_id=session.id, role="user", content=text))

    # 既に有人モードの場合は自動返信しない（管理者が手動対応）
    if session.status == "human":
        session.unread_count += 1
        db.commit()
        return

    # 有人要求キーワード検出
    if any(w in text for w in _HUMAN_TRIGGER_WORDS):
        await _escalate_to_human(session, store, access_token, reply_token, db)
        return

    # アクティブなFAQアイテムを取得
    faqs = db.query(FAQItem).filter(
        FAQItem.store_id == store.id,
        FAQItem.is_active == True,
    ).order_by(FAQItem.sort_order, FAQItem.created_at).all()

    if not faqs:
        # FAQが未登録の場合はデフォルト返答
        bot_reply = "ご質問ありがとうございます。担当者より折り返しご連絡いたします。"
        await _send_bot_reply(session, access_token, reply_token, bot_reply, db)
        db.commit()
        return

    # Step 1: キーワードマッチ
    answer = _keyword_match(text, faqs)

    # Step 2: Claude NLP
    if not answer:
        answer = await _claude_match(text, faqs, store.name)

    if answer and answer != _CANNOT_ANSWER_MARKER:
        await _send_bot_reply(session, access_token, reply_token, answer, db)
        db.commit()
    else:
        await _escalate_to_human(session, store, access_token, reply_token, db)


def _keyword_match(text: str, faqs: list[FAQItem]) -> str | None:
    """キーワードが含まれるFAQを検索して回答を返す"""
    text_lower = text.lower()
    for faq in faqs:
        if not faq.keywords:
            continue
        keywords = [k.strip() for k in faq.keywords.split(",") if k.strip()]
        if any(kw.lower() in text_lower for kw in keywords):
            return faq.answer
    return None


async def _claude_match(text: str, faqs: list[FAQItem], store_name: str) -> str:
    """Claude APIでFAQリストから意図を汲み取って回答する"""
    if not settings.anthropic_api_key:
        return _CANNOT_ANSWER_MARKER

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        faq_text = "\n".join(
            f"Q: {f.question}\nA: {f.answer}" for f in faqs
        )

        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=(
                f"あなたは{store_name}のカスタマーサポートAIです。"
                "以下のFAQリストを参考に、ユーザーの質問に日本語で簡潔に答えてください。"
                f"FAQの範囲外で答えられない場合は必ず「{_CANNOT_ANSWER_MARKER}」とだけ返してください。"
                "それ以外の場合は{_CANNOT_ANSWER_MARKER}を含めないでください。"
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"FAQリスト:\n{faq_text}\n\nユーザーの質問: {text}",
                }
            ],
        )
        reply = message.content[0].text.strip()
        return reply if reply else _CANNOT_ANSWER_MARKER

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return _CANNOT_ANSWER_MARKER


async def _send_bot_reply(
    session: ChatSession,
    access_token: str,
    reply_token: str,
    text: str,
    db: Session,
) -> None:
    db.add(ChatMessage(session_id=session.id, role="bot", content=text))
    await reply_line_message(access_token, reply_token, [{"type": "text", "text": text}])


async def _escalate_to_human(
    session: ChatSession,
    store: Store,
    access_token: str,
    reply_token: str,
    db: Session,
) -> None:
    """有人対応へ切り替え、管理者にLINE通知を送る"""
    session.status = "human"
    session.unread_count += 1

    user_msg = "少々お待ちください。担当スタッフがご対応いたします。"
    db.add(ChatMessage(session_id=session.id, role="bot", content=user_msg))
    await reply_line_message(access_token, reply_token, [{"type": "text", "text": user_msg}])

    # 管理者のLINE IDが設定されていれば通知（store.notify_line_user_idがあれば）
    # TODO: 管理者LINE IDをStoreSettingsに追加後に有効化
    # notify_id = store.settings.notify_line_user_id if store.settings else None
    # if notify_id:
    #     await send_line_message(access_token, notify_id, [{
    #         "type": "text",
    #         "text": f"[有人対応リクエスト]\n{session.display_name or 'ユーザー'} さんから対応依頼が届きました。\n管理画面でチャットを確認してください。"
    #     }])

    db.commit()
