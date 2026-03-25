from __future__ import annotations
from datetime import datetime, date, timedelta, time, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.store import Store, StoreSettings, BusinessHours, Holiday, ReservationBlock
from ..models.staff import Staff, StaffMenuSettings
from ..models.menu import Menu
from ..models.reservation import Reservation
from ..industry.base import TimeSlot


def get_available_slots(
    db: Session,
    store: Store,
    target_date: date,
    menu_id: str,
    staff_id: Optional[str] = None,
) -> list[TimeSlot]:
    """
    指定日・メニュー・スタッフの空き枠を返す。
    staff_id=None の場合は、対応可能ないずれかのスタッフの空き枠を返す。
    """
    settings = store.settings
    if not settings:
        return []

    # 休業日チェック
    date_str = target_date.strftime("%Y-%m-%d")
    holiday = db.query(Holiday).filter(
        Holiday.store_id == store.id,
        Holiday.date == date_str,
    ).first()
    if holiday:
        return []

    # 営業時間取得（0=日,1=月,...,6=土）
    day_of_week = target_date.weekday()  # 0=月,...,6=日 (Python)
    # Python: 0=月, 6=日 → 変換: 月=1,火=2,...,日=0
    day_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}
    store_dow = day_map[day_of_week]

    bh = db.query(BusinessHours).filter(
        BusinessHours.store_id == store.id,
        BusinessHours.day_of_week == store_dow,
    ).first()

    if not bh or not bh.is_open or not bh.open_time or not bh.close_time:
        return []

    # 対象メニュー取得
    menu = db.query(Menu).filter(Menu.id == menu_id, Menu.store_id == store.id, Menu.is_active == True).first()
    if not menu:
        return []

    total_minutes = menu.duration_minutes + menu.buffer_minutes
    slot_minutes = settings.slot_duration_minutes

    # 対象スタッフリスト決定
    if staff_id:
        staff_list = db.query(Staff).filter(
            Staff.id == staff_id,
            Staff.store_id == store.id,
            Staff.is_active == True,
        ).all()
    else:
        # メニューに対応可能な全スタッフ（StaffMenuSettingsがあれば絞り込む）
        menu_staff_ids = [
            r.staff_id for r in db.query(StaffMenuSettings.staff_id).filter(
                StaffMenuSettings.menu_id == menu_id,
                StaffMenuSettings.is_available == True,
            ).all()
        ]
        base_query = db.query(Staff).filter(
            Staff.store_id == store.id,
            Staff.is_active == True,
            Staff.is_assignable == True,
        )
        if menu_staff_ids:
            staff_list = base_query.filter(Staff.id.in_(menu_staff_ids)).all()
        else:
            # StaffMenuSettings未設定の場合は全アクティブスタッフを対象にする
            staff_list = base_query.all()

    if not staff_list:
        return []

    # スロット生成（施術開始時刻の候補）
    open_dt = datetime.combine(target_date, bh.open_time, tzinfo=timezone.utc)
    close_dt = datetime.combine(target_date, bh.close_time, tzinfo=timezone.utc)

    # 各スタッフの既存予約を取得
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    existing_reservations = db.query(Reservation).filter(
        Reservation.store_id == store.id,
        Reservation.staff_id.in_([s.id for s in staff_list]),
        Reservation.status.notin_(["cancelled", "no_show"]),
        Reservation.start_datetime < day_end,
        Reservation.end_datetime > day_start,
    ).all()

    # 予約ブロックを取得
    blocks = db.query(ReservationBlock).filter(
        ReservationBlock.store_id == store.id,
        or_(
            ReservationBlock.staff_id.in_([s.id for s in staff_list]),
            ReservationBlock.staff_id == None,
        ),
        ReservationBlock.start_datetime < day_end,
        ReservationBlock.end_datetime > day_start,
    ).all()

    result_slots: list[TimeSlot] = []
    seen_starts: set[datetime] = set()  # 同一時刻の重複防止

    for staff in staff_list:
        # このスタッフの使用済み時間帯
        busy_ranges = [
            (r.start_datetime, r.end_datetime)
            for r in existing_reservations
            if r.staff_id == staff.id
        ]
        # スタッフまたは全体のブロック
        block_ranges = [
            (b.start_datetime, b.end_datetime)
            for b in blocks
            if b.staff_id == staff.id or b.staff_id is None
        ]
        all_busy = busy_ranges + block_ranges

        # スタッフ固有の施術時間があれば上書き
        sms = db.query(StaffMenuSettings).filter(
            StaffMenuSettings.staff_id == staff.id,
            StaffMenuSettings.menu_id == menu_id,
        ).first()
        staff_duration = (sms.custom_duration_minutes or menu.duration_minutes) if sms else menu.duration_minutes
        staff_total = staff_duration + menu.buffer_minutes

        # スロット候補を生成
        current = open_dt
        while current + timedelta(minutes=staff_total) <= close_dt:
            slot_end = current + timedelta(minutes=staff_total)

            # 最低予約受付時間チェック（X時間前まで）
            now = datetime.now(timezone.utc)
            min_booking_dt = now + timedelta(hours=settings.min_booking_hours)
            if current < min_booking_dt:
                current += timedelta(minutes=slot_minutes)
                continue

            # 先の予約可能日数チェック
            max_booking_dt = now + timedelta(days=settings.advance_booking_days)
            if current > max_booking_dt:
                break

            # ビジー範囲と重複チェック
            is_free = True
            for busy_start, busy_end in all_busy:
                if current < busy_end and slot_end > busy_start:
                    is_free = False
                    break

            if is_free:
                # staff_id=None（おまかせ）の場合は同一時刻スロットを1件に集約
                slot_key = current if staff_id else current
                if not staff_id and current in seen_starts:
                    current += timedelta(minutes=slot_minutes)
                    continue

                result_slots.append(TimeSlot(
                    start=current,
                    end=slot_end,
                    staff_id=staff.id,
                    staff_name=staff.name,
                ))
                if not staff_id:
                    seen_starts.add(current)

            current += timedelta(minutes=slot_minutes)

    # 時刻順にソート
    result_slots.sort(key=lambda s: s.start)
    return result_slots
