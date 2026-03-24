from __future__ import annotations
import hashlib
import hmac
import base64
import json
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.store import Store
from ..services.line_service import reply_line_message, build_booking_flex_message
from ..config import settings
from ..core.logging import logger

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _verify_line_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    """LINE Webhookの署名を検証する"""
    hash_val = hmac.new(
        channel_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(hash_val).decode("utf-8")
    return hmac.compare_digest(expected, signature)


@router.post("/line/{store_id}")
async def line_webhook(
    store_id: str,
    request: Request,
    x_line_signature: str = Header(...),
    db: Session = Depends(get_db),
):
    body = await request.body()

    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    channel_secret = store.line_channel_secret or settings.line_channel_secret
    if not channel_secret:
        raise HTTPException(status_code=500, detail="LINE channel secret not configured")

    if not _verify_line_signature(body, x_line_signature, channel_secret):
        logger.warning("Invalid LINE signature", extra={"store_id": store_id})
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    access_token = store.line_access_token or settings.line_channel_access_token
    liff_id = store.liff_id or settings.line_liff_id

    for event in payload.get("events", []):
        await _process_event(event, store, access_token, liff_id)

    return {"status": "ok"}


async def _process_event(event: dict, store: Store, access_token: str, liff_id: str):
    event_type = event.get("type")
    reply_token = event.get("replyToken")

    if event_type == "follow":
        # 友達追加時のウェルカムメッセージ
        await reply_line_message(
            access_token,
            reply_token,
            [{"type": "text", "text": f"{store.name}へようこそ！\nご予約はこちらからお願いします。"}],
        )

    elif event_type == "message":
        msg = event.get("message", {})
        if msg.get("type") == "text":
            text = msg.get("text", "").strip()
            if "予約" in text:
                liff_url = f"https://liff.line.me/{liff_id}?store_id={store.id}"
                flex_msg = build_booking_flex_message(liff_url, store.name)
                await reply_line_message(access_token, reply_token, [flex_msg])
            else:
                await reply_line_message(
                    access_token,
                    reply_token,
                    [{
                        "type": "text",
                        "text": "ご予約・確認はメニューからお選びください。",
                        "quickReply": {
                            "items": [
                                {
                                    "type": "action",
                                    "action": {
                                        "type": "uri",
                                        "label": "予約する",
                                        "uri": f"https://liff.line.me/{liff_id}?store_id={store.id}&action=book",
                                    },
                                },
                                {
                                    "type": "action",
                                    "action": {
                                        "type": "uri",
                                        "label": "予約確認",
                                        "uri": f"https://liff.line.me/{liff_id}?store_id={store.id}&action=list",
                                    },
                                },
                            ]
                        },
                    }],
                )

    elif event_type == "postback":
        data = event.get("postback", {}).get("data", "")
        params = dict(p.split("=") for p in data.split("&") if "=" in p)
        action = params.get("action", "")
        reservation_id = params.get("reservation_id", "")

        liff_base = f"https://liff.line.me/{liff_id}"

        if action == "view_reservation":
            url = f"{liff_base}?page=my-reservations&store_id={store.id}"
        elif action == "cancel_reservation":
            url = f"{liff_base}?page=cancel&reservation_id={reservation_id}&store_id={store.id}"
        else:
            url = f"{liff_base}?store_id={store.id}&action=book"

        flex_msg = {
            "type": "flex",
            "altText": "予約の操作",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "予約の操作を選択してください", "wrap": True}
                    ],
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {"type": "uri", "label": "確認・変更・取消", "uri": url},
                        }
                    ],
                },
            },
        }
        await reply_line_message(access_token, reply_token, [flex_msg])


@router.post("/google/{store_id}")
async def google_calendar_webhook(
    store_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """GoogleカレンダーのPush通知を受信し、外部イベントを予約ブロックとして登録する"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        return {"status": "ignored"}

    resource_state = request.headers.get("X-Goog-Resource-State")

    if resource_state == "sync":
        # 初期同期確認リクエスト
        return {"status": "synced"}

    if resource_state == "exists":
        # カレンダーに変更があった → 差分取得・ブロック反映
        logger.info("Google Calendar webhook received", extra={"store_id": store_id})
        # TODO: 変更されたイベントを取得し、DB予約と照合してブロック登録
        # 実装詳細は google_calendar_service.py の sync 関数で行う

    return {"status": "ok"}
