from __future__ import annotations
import httpx
from typing import Optional
from ..core.logging import logger


async def get_line_profile(access_token: str) -> Optional[dict]:
    """LINEアクセストークンからユーザープロフィールを取得"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.line.me/v2/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5.0,
        )
    if resp.status_code == 200:
        return resp.json()
    logger.warning("Failed to get LINE profile", extra={"status": resp.status_code})
    return None


async def send_line_message(access_token: str, user_id: str, messages: list[dict]) -> bool:
    """LINE Messaging APIでプッシュメッセージを送信"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"to": user_id, "messages": messages},
            timeout=10.0,
        )
    if resp.status_code == 200:
        return True
    logger.error(
        "Failed to send LINE message",
        extra={"user_id": user_id, "status": resp.status_code, "body": resp.text},
    )
    return False


async def send_line_text_message(access_token: str, user_id: str, text: str) -> bool:
    return await send_line_message(
        access_token, user_id,
        [{"type": "text", "text": text}],
    )


async def reply_line_message(channel_access_token: str, reply_token: str, messages: list[dict]) -> bool:
    """Webhookイベントへの返信"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Authorization": f"Bearer {channel_access_token}",
                "Content-Type": "application/json",
            },
            json={"replyToken": reply_token, "messages": messages},
            timeout=10.0,
        )
    return resp.status_code == 200


def build_booking_flex_message(liff_url: str, store_name: str) -> dict:
    """予約開始用のFlexメッセージを組み立てる"""
    return {
        "type": "flex",
        "altText": f"{store_name}のご予約はこちら",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": store_name,
                        "weight": "bold",
                        "size": "xl",
                    }
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "ご予約の受付を開始します。\n下のボタンからご希望の日時をお選びください。",
                        "wrap": True,
                    }
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "uri",
                            "label": "予約する",
                            "uri": liff_url,
                        },
                    }
                ],
            },
        },
    }
