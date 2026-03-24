from __future__ import annotations
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.reservation import Reservation, ReservationHistory
from ..models.customer import Customer
from ..models.staff import Staff, StaffMenuSettings
from ..models.menu import Menu
from ..models.store import Store, StoreSettings
from ..models.log import AuditLog
from ..core.security import generate_confirmation_code
from ..core.exceptions import (
    DoubleBookingError,
    BlacklistedCustomerError,
    NotFoundError,
    ValidationError,
    CancellationNotAllowedError,
)
from ..industry.registry import get_template
from .availability_service import get_available_slots
from .notification_service import send_notification_async


def _check_double_booking(
    db: Session,
    store_id: str,
    staff_id: str,
    start_dt: datetime,
    end_dt: datetime,
    exclude_reservation_id: Optional[str] = None,
) -> bool:
    """指定スタッフ・時間帯の重複予約があるか確認する（Trueなら重複あり）"""
    query = db.query(Reservation).filter(
        Reservation.store_id == store_id,
        Reservation.staff_id == staff_id,
        Reservation.status.notin_(["cancelled", "no_show"]),
        Reservation.start_datetime < end_dt,
        Reservation.end_datetime > start_dt,
    )
    if exclude_reservation_id:
        query = query.filter(Reservation.id != exclude_reservation_id)

    return query.first() is not None


def _record_history(
    db: Session,
    reservation: Reservation,
    change_type: str,
    before_data: Optional[dict],
    after_data: Optional[dict],
    actor_type: str,
    actor_id: str,
) -> None:
    history = ReservationHistory(
        reservation_id=reservation.id,
        changed_by_type=actor_type,
        changed_by_id=actor_id,
        change_type=change_type,
        before_data=before_data,
        after_data=after_data,
    )
    db.add(history)


def _reservation_to_dict(r: Reservation) -> dict:
    return {
        "id": r.id,
        "status": r.status,
        "start_datetime": r.start_datetime.isoformat() if r.start_datetime else None,
        "end_datetime": r.end_datetime.isoformat() if r.end_datetime else None,
        "staff_id": r.staff_id,
        "menu_id": r.menu_id,
        "notes": r.notes,
    }


def create_reservation(
    db: Session,
    store: Store,
    customer: Customer,
    menu_id: str,
    start_datetime: datetime,
    staff_id: Optional[str],
    notes: Optional[str],
    is_first_visit: Optional[bool],
    extra_data: dict,
    actor_type: str,
    actor_id: str,
    is_proxy: bool = False,
    proxy_registered_by: Optional[str] = None,
) -> Reservation:
    # ブラックリストチェック
    if customer.is_blacklisted:
        raise BlacklistedCustomerError()

    # メニュー取得
    menu = db.query(Menu).filter(Menu.id == menu_id, Menu.store_id == store.id, Menu.is_active == True).first()
    if not menu:
        raise NotFoundError("Menu", menu_id)

    # スタッフ取得・対応可否チェック
    if staff_id:
        staff = db.query(Staff).filter(Staff.id == staff_id, Staff.store_id == store.id, Staff.is_active == True).first()
        if not staff:
            raise NotFoundError("Staff", staff_id)

        sms = db.query(StaffMenuSettings).filter(
            StaffMenuSettings.staff_id == staff_id,
            StaffMenuSettings.menu_id == menu_id,
        ).first()
        if sms and not sms.is_available:
            raise ValidationError(f"指定のスタッフはこのメニューを担当できません。")

        # スタッフ固有の施術時間
        duration = (sms.custom_duration_minutes or menu.duration_minutes) if sms else menu.duration_minutes
    else:
        duration = menu.duration_minutes

    end_datetime = start_datetime + timedelta(minutes=duration + menu.buffer_minutes)

    # ダブルブッキング事前チェック（楽観的チェック）
    if staff_id and _check_double_booking(db, store.id, staff_id, start_datetime, end_datetime):
        raise DoubleBookingError()

    # 予約モード決定
    store_settings = store.settings
    menu_booking_mode = menu.booking_mode
    if menu_booking_mode == "inherit":
        booking_mode = store_settings.booking_mode if store_settings else "auto"
    else:
        booking_mode = menu_booking_mode

    status = "pending" if booking_mode == "approval" else "confirmed"

    reservation = Reservation(
        store_id=store.id,
        customer_id=customer.id,
        staff_id=staff_id,
        menu_id=menu_id,
        status=status,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        notes=notes,
        is_first_visit=is_first_visit,
        is_proxy=is_proxy,
        proxy_registered_by=proxy_registered_by,
        confirmation_code=generate_confirmation_code(),
        extra_data=extra_data,
    )
    db.add(reservation)

    try:
        db.flush()  # IDを確定させる（コミット前）
    except IntegrityError:
        db.rollback()
        raise DoubleBookingError()  # DB制約で弾かれた場合

    _record_history(
        db, reservation, "created",
        before_data=None,
        after_data=_reservation_to_dict(reservation),
        actor_type=actor_type,
        actor_id=actor_id,
    )

    # 顧客の初回フラグ更新
    if customer.is_first_visit and status == "confirmed":
        customer.is_first_visit = False
        customer.visit_count = (customer.visit_count or 0) + 1

    db.commit()
    db.refresh(reservation)

    return reservation


def update_reservation(
    db: Session,
    reservation: Reservation,
    new_start_datetime: Optional[datetime],
    new_staff_id: Optional[str],
    new_notes: Optional[str],
    actor_type: str,
    actor_id: str,
) -> Reservation:
    before = _reservation_to_dict(reservation)

    if new_start_datetime:
        menu = db.query(Menu).filter(Menu.id == reservation.menu_id).first()
        if not menu:
            raise NotFoundError("Menu")

        staff_id = new_staff_id or reservation.staff_id
        sms = None
        if staff_id:
            sms = db.query(StaffMenuSettings).filter(
                StaffMenuSettings.staff_id == staff_id,
                StaffMenuSettings.menu_id == reservation.menu_id,
            ).first()
        duration = (sms.custom_duration_minutes or menu.duration_minutes) if sms else menu.duration_minutes
        new_end = new_start_datetime + timedelta(minutes=duration + menu.buffer_minutes)

        if staff_id and _check_double_booking(
            db, reservation.store_id, staff_id, new_start_datetime, new_end,
            exclude_reservation_id=reservation.id
        ):
            raise DoubleBookingError()

        reservation.start_datetime = new_start_datetime
        reservation.end_datetime = new_end

    if new_staff_id is not None:
        reservation.staff_id = new_staff_id
    if new_notes is not None:
        reservation.notes = new_notes

    _record_history(db, reservation, "updated", before, _reservation_to_dict(reservation), actor_type, actor_id)
    db.commit()
    db.refresh(reservation)
    return reservation


def cancel_reservation(
    db: Session,
    reservation: Reservation,
    reason: Optional[str],
    actor_type: str,
    actor_id: str,
) -> Reservation:
    # キャンセルポリシーチェック
    menu = db.query(Menu).filter(Menu.id == reservation.menu_id).first()
    policy = None
    if menu and menu.cancellation_policy_id:
        from ..models.notification import CancellationPolicy
        policy = db.query(CancellationPolicy).filter(CancellationPolicy.id == menu.cancellation_policy_id).first()
    if not policy:
        # 店舗デフォルトポリシーを使用
        settings = reservation.store.settings if reservation.store else None
        if settings and settings.default_cancellation_policy_id:
            from ..models.notification import CancellationPolicy
            policy = db.query(CancellationPolicy).filter(CancellationPolicy.id == settings.default_cancellation_policy_id).first()

    if policy and actor_type == "customer":
        now = datetime.now(timezone.utc)
        # 当日キャンセル不可チェック
        if not policy.same_day_cancel_allowed:
            if reservation.start_datetime.date() == now.date():
                raise CancellationNotAllowedError("当日のキャンセルはできません。")
        # 期限チェック
        if policy.cancel_deadline_hours is not None:
            deadline = reservation.start_datetime - timedelta(hours=policy.cancel_deadline_hours)
            if now > deadline:
                raise CancellationNotAllowedError(
                    f"キャンセルは予約の{policy.cancel_deadline_hours}時間前まで可能です。"
                )
        # 理由入力が必須かチェック
        if policy.require_cancel_reason and not reason:
            raise ValidationError("キャンセル理由を入力してください。")

    before = _reservation_to_dict(reservation)
    reservation.status = "cancelled"
    reservation.cancellation_reason = reason
    reservation.cancelled_at = datetime.now(timezone.utc)
    reservation.cancelled_by_type = actor_type
    reservation.cancelled_by_id = actor_id

    # 顧客のキャンセルカウント更新
    customer = reservation.customer
    if customer and actor_type == "customer":
        customer.cancel_count = (customer.cancel_count or 0) + 1

    _record_history(db, reservation, "cancelled", before, _reservation_to_dict(reservation), actor_type, actor_id)
    db.commit()
    db.refresh(reservation)
    return reservation
