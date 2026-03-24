"""
ダブルブッキング防止テスト。
同一スタッフ・重複時間帯への予約は拒否されることを確認する。
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.models.reservation import Reservation
from app.models.customer import Customer
from app.services.reservation_service import create_reservation
from app.core.exceptions import DoubleBookingError


def _dt(offset_days=30, hour=10, minute=0):
    """指定日時のUTC datetimeを返す"""
    now = datetime.now(timezone.utc)
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=offset_days)


def test_no_double_booking_same_staff_overlap(db, seed_data):
    """同一スタッフの重複時間帯は DoubleBookingError になること"""
    store = seed_data["store"]
    staff = seed_data["staff"]
    menu = seed_data["menu"]  # 60分メニュー

    customer1 = Customer(
        store_id=store.id,
        line_user_id="Utest_double1",
        name="顧客1",
        phone="090-0001-0001",
    )
    db.add(customer1)
    customer2 = Customer(
        store_id=store.id,
        line_user_id="Utest_double2",
        name="顧客2",
        phone="090-0002-0002",
    )
    db.add(customer2)
    db.flush()

    # 1件目: 10:00-11:00
    start1 = _dt(30, 10, 0)
    r1 = create_reservation(
        db=db,
        store=store,
        customer=customer1,
        menu_id=menu.id,
        start_datetime=start1,
        staff_id=staff.id,
        notes=None,
        is_first_visit=True,
        extra_data={},
        actor_type="admin",
        actor_id="test",
    )
    assert r1.status == "confirmed"

    # 2件目: 10:30-11:30 → 重複 → DoubleBookingError
    start2 = _dt(30, 10, 30)
    with pytest.raises(DoubleBookingError):
        create_reservation(
            db=db,
            store=store,
            customer=customer2,
            menu_id=menu.id,
            start_datetime=start2,
            staff_id=staff.id,
            notes=None,
            is_first_visit=True,
            extra_data={},
            actor_type="admin",
            actor_id="test",
        )


def test_no_double_booking_exact_same_time(db, seed_data):
    """まったく同じ時刻・同一スタッフは2件目がエラーになること"""
    store = seed_data["store"]
    staff = seed_data["staff"]
    menu = seed_data["menu"]

    customers = []
    for i in range(2):
        c = Customer(
            store_id=store.id,
            line_user_id=f"Utest_exact{i}",
            name=f"顧客{i}",
            phone=f"090-{i:04d}-0000",
        )
        db.add(c)
        customers.append(c)
    db.flush()

    start = _dt(31, 14, 0)

    create_reservation(
        db=db, store=store, customer=customers[0], menu_id=menu.id,
        start_datetime=start, staff_id=staff.id, notes=None,
        is_first_visit=True, extra_data={}, actor_type="admin", actor_id="test",
    )

    with pytest.raises(DoubleBookingError):
        create_reservation(
            db=db, store=store, customer=customers[1], menu_id=menu.id,
            start_datetime=start, staff_id=staff.id, notes=None,
            is_first_visit=True, extra_data={}, actor_type="admin", actor_id="test",
        )


def test_allow_different_staff_same_time(db, seed_data):
    """異なるスタッフなら同一時刻でも予約できること"""
    from app.models.staff import Staff as StaffModel

    store = seed_data["store"]
    menu = seed_data["menu"]
    staff1 = seed_data["staff"]

    staff2 = StaffModel(store_id=store.id, name="スタッフ2", is_active=True, is_assignable=True)
    db.add(staff2)

    customers = []
    for i in range(2):
        c = Customer(
            store_id=store.id,
            line_user_id=f"Utest_diff_staff{i}",
            name=f"顧客{i}",
            phone=f"090-{i+10:04d}-0000",
        )
        db.add(c)
        customers.append(c)
    db.flush()

    start = _dt(32, 10, 0)

    r1 = create_reservation(
        db=db, store=store, customer=customers[0], menu_id=menu.id,
        start_datetime=start, staff_id=staff1.id, notes=None,
        is_first_visit=True, extra_data={}, actor_type="admin", actor_id="test",
    )
    r2 = create_reservation(
        db=db, store=store, customer=customers[1], menu_id=menu.id,
        start_datetime=start, staff_id=staff2.id, notes=None,
        is_first_visit=True, extra_data={}, actor_type="admin", actor_id="test",
    )

    assert r1.status == "confirmed"
    assert r2.status == "confirmed"


def test_allow_after_cancellation(db, seed_data):
    """キャンセル済み予約と同一時刻に新規予約できること"""
    from app.services.reservation_service import cancel_reservation

    store = seed_data["store"]
    staff = seed_data["staff"]
    menu = seed_data["menu"]

    customers = []
    for i in range(2):
        c = Customer(
            store_id=store.id,
            line_user_id=f"Utest_after_cancel{i}",
            name=f"顧客{i}",
            phone=f"090-{i+20:04d}-0000",
        )
        db.add(c)
        customers.append(c)
    db.flush()

    start = _dt(33, 15, 0)

    r1 = create_reservation(
        db=db, store=store, customer=customers[0], menu_id=menu.id,
        start_datetime=start, staff_id=staff.id, notes=None,
        is_first_visit=True, extra_data={}, actor_type="admin", actor_id="test",
    )

    # キャンセル
    cancel_reservation(db=db, reservation=r1, reason="テスト", actor_type="admin", actor_id="test")

    # キャンセル後は同一時刻に予約できる
    r2 = create_reservation(
        db=db, store=store, customer=customers[1], menu_id=menu.id,
        start_datetime=start, staff_id=staff.id, notes=None,
        is_first_visit=True, extra_data={}, actor_type="admin", actor_id="test",
    )
    assert r2.status == "confirmed"


def test_blacklisted_customer_cannot_book(db, seed_data):
    """ブラックリスト顧客は予約できないこと"""
    from app.core.exceptions import BlacklistedCustomerError

    store = seed_data["store"]
    staff = seed_data["staff"]
    menu = seed_data["menu"]

    bl_customer = Customer(
        store_id=store.id,
        line_user_id="Utest_blacklist",
        name="BL顧客",
        phone="090-9999-9999",
        is_blacklisted=True,
        blacklist_reason="テスト",
    )
    db.add(bl_customer)
    db.flush()

    with pytest.raises(BlacklistedCustomerError):
        create_reservation(
            db=db, store=store, customer=bl_customer, menu_id=menu.id,
            start_datetime=_dt(34, 10, 0), staff_id=staff.id, notes=None,
            is_first_visit=False, extra_data={}, actor_type="customer", actor_id="Utest_blacklist",
        )
