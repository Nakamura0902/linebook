from __future__ import annotations
import re
import asyncio
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from ..models.reservation import Reservation
from ..models.notification import NotificationTemplate, NotificationLog
from ..models.customer import Customer
from ..models.store import Store
from ..core.logging import logger
from .line_service import send_line_text_message

# 通知テンプレートの変数置換パターン: {{variable_name}}
_TEMPLATE_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def _build_template_vars(reservation: Reservation, store: Store) -> dict:
    """テンプレート変数辞書を構築する"""
    start = reservation.start_datetime
    customer = reservation.customer
    staff = reservation.staff
    menu = reservation.menu

    return {
        "store_name": store.name,
        "customer_name": customer.name or "お客様",
        "reservation_date": start.strftime("%Y年%m月%d日") if start else "",
        "reservation_time": start.strftime("%H:%M") if start else "",
        "end_time": reservation.end_datetime.strftime("%H:%M") if reservation.end_datetime else "",
        "staff_name": staff.name if staff else "指定なし",
        "menu_name": menu.name if menu else "",
        "confirmation_code": reservation.confirmation_code or "",
        "cancel_reason": reservation.cancellation_reason or "",
        "store_phone": store.phone or "",
    }


def _render_template(template_body: str, variables: dict) -> str:
    """{{変数名}} を実際の値に置換する"""
    def replace(match):
        key = match.group(1)
        return str(variables.get(key, f"{{{{{key}}}}}"))
    return _TEMPLATE_VAR_RE.sub(replace, template_body)


async def send_notification(
    db: Session,
    reservation: Reservation,
    notification_type: str,
    store: Store,
) -> bool:
    """
    指定タイプの通知をユーザーに送信する。
    通知ログを記録し、失敗時は管理者アラートを発火する。
    """
    template = db.query(NotificationTemplate).filter(
        NotificationTemplate.store_id == store.id,
        NotificationTemplate.type == notification_type,
        NotificationTemplate.channel == "line",
        NotificationTemplate.is_active == True,
    ).first()

    if not template:
        logger.info(f"No notification template for type={notification_type}, store={store.id}")
        return False

    customer = reservation.customer
    if not customer or not customer.line_user_id:
        return False

    variables = _build_template_vars(reservation, store)
    message_text = _render_template(template.body, variables)

    log = NotificationLog(
        reservation_id=reservation.id,
        customer_id=customer.id,
        template_type=notification_type,
        channel="line",
        recipient=customer.line_user_id,
        status="pending",
    )
    db.add(log)
    db.flush()

    access_token = store.line_access_token
    if not access_token:
        log.status = "failed"
        log.error_message = "LINE access token not configured"
        db.commit()
        return False

    success = await send_line_text_message(access_token, customer.line_user_id, message_text)

    if success:
        log.status = "sent"
        log.sent_at = datetime.now(timezone.utc)
    else:
        log.status = "failed"
        log.error_message = "LINE API returned error"
        # 通知失敗を管理者に通知
        await _alert_admin_notification_failure(store, notification_type, reservation.id)

    db.commit()
    return success


async def send_admin_notification(
    db: Session,
    reservation: Reservation,
    notification_type: str,
    store: Store,
    admin_line_user_id: Optional[str] = None,
) -> bool:
    """管理者向け通知を送信する"""
    template = db.query(NotificationTemplate).filter(
        NotificationTemplate.store_id == store.id,
        NotificationTemplate.type == notification_type,
        NotificationTemplate.channel == "line",
        NotificationTemplate.is_active == True,
    ).first()

    if not template or not admin_line_user_id:
        return False

    variables = _build_template_vars(reservation, store)
    message_text = _render_template(template.body, variables)

    access_token = store.line_access_token
    if not access_token:
        return False

    return await send_line_text_message(access_token, admin_line_user_id, message_text)


async def _alert_admin_notification_failure(
    store: Store,
    notification_type: str,
    reservation_id: str,
) -> None:
    """通知失敗時に管理者へアラートを送る（ベストエフォート）"""
    logger.error(
        "Notification failed",
        extra={
            "store_id": store.id,
            "notification_type": notification_type,
            "reservation_id": reservation_id,
        },
    )
    # TODO: 管理者LINEまたはメールへのアラート送信実装


def send_notification_async(
    db_factory,
    reservation_id: str,
    notification_type: str,
    store_id: str,
) -> None:
    """非同期タスクとして通知送信をスケジュールする（バックグラウンド）"""
    # FastAPIのBackgroundTasksから呼ばれることを想定
    pass  # 実際の実装はrouter層でBackgroundTasksを使用


def get_default_templates(store_id: str) -> list[dict]:
    """新規店舗作成時のデフォルト通知テンプレート一覧"""
    return [
        {
            "store_id": store_id,
            "type": "booking_confirmed",
            "channel": "line",
            "body": (
                "【予約確定】{{store_name}}\n\n"
                "{{customer_name}} 様\n"
                "ご予約が確定しました。\n\n"
                "日時: {{reservation_date}} {{reservation_time}}〜{{end_time}}\n"
                "担当: {{staff_name}}\n"
                "メニュー: {{menu_name}}\n"
                "予約番号: {{confirmation_code}}\n\n"
                "ご来店をお待ちしております。"
            ),
        },
        {
            "store_id": store_id,
            "type": "booking_changed",
            "channel": "line",
            "body": (
                "【予約変更】{{store_name}}\n\n"
                "{{customer_name}} 様\n"
                "ご予約の内容が変更されました。\n\n"
                "日時: {{reservation_date}} {{reservation_time}}〜{{end_time}}\n"
                "担当: {{staff_name}}\n"
                "メニュー: {{menu_name}}\n"
                "予約番号: {{confirmation_code}}"
            ),
        },
        {
            "store_id": store_id,
            "type": "booking_cancelled",
            "channel": "line",
            "body": (
                "【予約取消】{{store_name}}\n\n"
                "{{customer_name}} 様\n"
                "ご予約をキャンセルしました。\n\n"
                "またのご利用をお待ちしております。\n"
                "ご不明な点は {{store_phone}} までご連絡ください。"
            ),
        },
        {
            "store_id": store_id,
            "type": "reminder",
            "channel": "line",
            "body": (
                "【前日リマインド】{{store_name}}\n\n"
                "{{customer_name}} 様\n"
                "明日のご予約のリマインドです。\n\n"
                "日時: {{reservation_date}} {{reservation_time}}\n"
                "担当: {{staff_name}}\n\n"
                "ご来店をお待ちしております。"
            ),
        },
        {
            "store_id": store_id,
            "type": "admin_new",
            "channel": "line",
            "body": (
                "【新規予約】{{store_name}}\n"
                "{{reservation_date}} {{reservation_time}}\n"
                "担当: {{staff_name}} / {{menu_name}}\n"
                "顧客: {{customer_name}}\n"
                "予約番号: {{confirmation_code}}"
            ),
        },
    ]
