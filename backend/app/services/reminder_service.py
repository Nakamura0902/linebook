from __future__ import annotations
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.reservation import Reservation
from ..models.store import Store, StoreSettings
from ..core.logging import logger
from .notification_service import send_notification


async def send_reminders() -> None:
    """
    前日リマインドを送信するバッチ処理。
    APSchedulerから毎時呼び出され、送信時刻が来た店舗の予約にリマインドを送る。
    """
    db: Session = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        # リマインド有効な全店舗設定を取得
        active_settings = db.query(StoreSettings).filter(
            StoreSettings.reminder_enabled == True,
        ).all()

        for settings in active_settings:
            store = db.query(Store).filter(Store.id == settings.store_id, Store.is_active == True).first()
            if not store:
                continue

            # 送信時刻チェック（現在時刻が設定時刻 ± 30分以内）
            if settings.reminder_send_time:
                send_hour = settings.reminder_send_time.hour
                send_minute = settings.reminder_send_time.minute
                # タイムゾーン変換（UTC→店舗タイムゾーン）は簡略化。将来改善
                if not (send_hour - 1 <= now.hour <= send_hour + 1):
                    continue

            # 明日の予約を取得
            tomorrow = (now + timedelta(days=1)).date()
            tomorrow_start = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)
            tomorrow_end = datetime.combine(tomorrow, datetime.max.time(), tzinfo=timezone.utc)

            reservations = db.query(Reservation).filter(
                Reservation.store_id == store.id,
                Reservation.status == "confirmed",
                Reservation.start_datetime >= tomorrow_start,
                Reservation.start_datetime <= tomorrow_end,
            ).all()

            for reservation in reservations:
                try:
                    await send_notification(db, reservation, "reminder", store)
                except Exception as e:
                    logger.error(
                        "Reminder send failed",
                        extra={"reservation_id": reservation.id, "error": str(e)},
                    )

    except Exception as e:
        logger.error("Reminder batch failed", extra={"error": str(e)})
    finally:
        db.close()
