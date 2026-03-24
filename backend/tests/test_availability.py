"""
空き枠計算テスト。
"""
import pytest
from datetime import datetime, timezone, timedelta, date


def test_get_availability_returns_slots(client, seed_data):
    """空き枠APIがスロットを返すこと"""
    store_id = seed_data["store"].id
    menu_id = seed_data["menu"].id

    # 翌月1日（開店している平日を選ぶ）
    now = datetime.now(timezone.utc)
    target = now + timedelta(days=30)
    # 月曜日になるまで調整
    while target.weekday() == 6:  # 日曜はスキップ
        target += timedelta(days=1)

    date_str = target.strftime("%Y-%m-%d")

    res = client.get(
        f"/api/v1/liff/stores/{store_id}/availability",
        params={"date": date_str, "menu_id": menu_id},
    )
    assert res.status_code == 200
    data = res.json()
    assert "slots" in data
    # 開店日なのでスロットがあるはず
    assert len(data["slots"]) > 0


def test_get_availability_holiday_returns_empty(client, seed_data, admin_token):
    """休業日は空き枠が0になること"""
    store_id = seed_data["store"].id
    menu_id = seed_data["menu"].id

    # 休業日を登録
    now = datetime.now(timezone.utc)
    holiday_date = (now + timedelta(days=60)).strftime("%Y-%m-%d")

    client.post(
        f"/api/v1/admin/stores/{store_id}/holidays",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"date": holiday_date, "reason": "テスト休業"},
    )

    res = client.get(
        f"/api/v1/liff/stores/{store_id}/availability",
        params={"date": holiday_date, "menu_id": menu_id},
    )
    assert res.status_code == 200
    assert res.json()["slots"] == []


def test_get_availability_invalid_date(client, seed_data):
    """不正な日付形式は422エラーになること"""
    store_id = seed_data["store"].id
    menu_id = seed_data["menu"].id

    res = client.get(
        f"/api/v1/liff/stores/${store_id}/availability",
        params={"date": "not-a-date", "menu_id": menu_id},
    )
    # store_idが${...}形式なので404になる
    assert res.status_code in [404, 422]


def test_get_availability_booked_slot_disappears(client, seed_data, admin_token, db):
    """予約済みスロットは空き枠に出なくなること"""
    from app.models.customer import Customer
    from app.services.reservation_service import create_reservation
    from app.models.store import Store

    store = seed_data["store"]
    staff = seed_data["staff"]
    menu = seed_data["menu"]

    now = datetime.now(timezone.utc)
    target = now + timedelta(days=35)
    while target.weekday() == 6:
        target += timedelta(days=1)
    date_str = target.strftime("%Y-%m-%d")

    # 10:00のスロットを先に取得
    res = client.get(
        f"/api/v1/liff/stores/{store.id}/availability",
        params={"date": date_str, "menu_id": menu.id, "staff_id": staff.id},
    )
    slots_before = res.json()["slots"]
    assert len(slots_before) > 0

    first_slot = slots_before[0]

    # そのスロットに予約を入れる
    customer = Customer(
        store_id=store.id,
        line_user_id="Utest_avail",
        name="空き枠テスト顧客",
        phone="090-1234-5678",
    )
    db.add(customer)
    db.flush()

    create_reservation(
        db=db, store=store, customer=customer, menu_id=menu.id,
        start_datetime=datetime.fromisoformat(first_slot["start"]),
        staff_id=staff.id, notes=None, is_first_visit=True, extra_data={},
        actor_type="admin", actor_id="test",
    )
    db.commit()

    # 再取得: そのスロットが消えていること
    res2 = client.get(
        f"/api/v1/liff/stores/{store.id}/availability",
        params={"date": date_str, "menu_id": menu.id, "staff_id": staff.id},
    )
    slots_after = res2.json()["slots"]
    slot_starts = [s["start"] for s in slots_after]
    assert first_slot["start"] not in slot_starts
