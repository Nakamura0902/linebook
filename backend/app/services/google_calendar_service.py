from __future__ import annotations
"""
Googleカレンダー連携サービス。

設計方針:
- DB側が正(Source of Truth)
- Gcalは表示補助レイヤー
- 予約確定時にGcalへ書き込み（非同期・失敗しても予約は確定）
- Gcal Webhookで外部イベントを受信し、予約ブロックとして登録
"""
import json
from datetime import datetime, timezone
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..core.logging import logger


def _build_credentials(refresh_token: str, client_id: str, client_secret: str) -> Credentials:
    from ..config import settings
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id or settings.google_client_id,
        client_secret=client_secret or settings.google_client_secret,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )


def create_calendar_event(
    refresh_token: str,
    calendar_id: str,
    title: str,
    description: str,
    start_dt: datetime,
    end_dt: datetime,
    reservation_id: str,
) -> Optional[str]:
    """予約をGoogleカレンダーイベントとして作成し、event_idを返す"""
    try:
        creds = _build_credentials(refresh_token, "", "")
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Tokyo"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Tokyo"},
            "extendedProperties": {
                "private": {"linebook_reservation_id": reservation_id}
            },
        }

        result = service.events().insert(calendarId=calendar_id, body=event).execute()
        return result.get("id")

    except HttpError as e:
        logger.error("Google Calendar insert failed", extra={"error": str(e), "reservation_id": reservation_id})
        return None


def update_calendar_event(
    refresh_token: str,
    calendar_id: str,
    event_id: str,
    title: str,
    description: str,
    start_dt: datetime,
    end_dt: datetime,
) -> bool:
    try:
        creds = _build_credentials(refresh_token, "", "")
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Tokyo"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Tokyo"},
        }

        service.events().patch(calendarId=calendar_id, eventId=event_id, body=event).execute()
        return True

    except HttpError as e:
        logger.error("Google Calendar update failed", extra={"error": str(e), "event_id": event_id})
        return False


def delete_calendar_event(
    refresh_token: str,
    calendar_id: str,
    event_id: str,
) -> bool:
    try:
        creds = _build_credentials(refresh_token, "", "")
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except HttpError as e:
        logger.error("Google Calendar delete failed", extra={"error": str(e), "event_id": event_id})
        return False


def setup_webhook(
    refresh_token: str,
    calendar_id: str,
    webhook_url: str,
    channel_id: str,
) -> Optional[dict]:
    """Gcal Push通知チャンネルを登録する"""
    try:
        creds = _build_credentials(refresh_token, "", "")
        service = build("calendar", "v3", credentials=creds)

        body = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_url,
        }
        result = service.events().watch(calendarId=calendar_id, body=body).execute()
        return result
    except HttpError as e:
        logger.error("Google Calendar webhook setup failed", extra={"error": str(e)})
        return None


def get_oauth_url(client_id: str, redirect_uri: str, scopes: list[str], state: str) -> str:
    """OAuth2認証URLを生成する"""
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": "",  # フロントでは不要
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=scopes,
    )
    flow.redirect_uri = redirect_uri
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="consent",
    )
    return auth_url


def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scopes: list[str],
    code: str,
) -> Optional[dict]:
    """認証コードをリフレッシュトークンと交換する"""
    from google_auth_oauthlib.flow import Flow
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=scopes,
        )
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        creds = flow.credentials
        return {
            "refresh_token": creds.refresh_token,
            "token": creds.token,
        }
    except Exception as e:
        logger.error("Google OAuth token exchange failed", extra={"error": str(e)})
        return None
