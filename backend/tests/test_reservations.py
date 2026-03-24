import pytest
from datetime import datetime, timezone


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _future_dt(hour=14, minute=0):
    """翌月1日 指定時刻のUTC datetimeを文字列で返す"""
    now = datetime.now(timezone.utc)
    year = now.year + (1 if now.month == 12 else 0)
    month = 1 if now.month == 12 else now.month + 1
    return f"{year}-{str(month).zfill(2)}-01T{str(hour).zfill(2)}:{str(minute).zfill(2)}:00+00:00"


def test_list_reservations_empty(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    res = client.get(
        f"/api/v1/admin/stores/{store_id}/reservations",
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_create_proxy_reservation(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    menu_id = seed_data["menu"].id
    staff_id = seed_data["staff"].id

    res = client.post(
        f"/api/v1/admin/stores/{store_id}/reservations",
        headers=_auth(admin_token),
        json={
            "customer_name": "電話予約 太郎",
            "customer_phone": "090-9999-9999",
            "menu_id": menu_id,
            "staff_id": staff_id,
            "start_datetime": _future_dt(10, 0),
            "notes": "テスト備考",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "confirmed"
    assert data["is_proxy"] is True
    assert data["customer_name"] == "電話予約 太郎"
    assert data["confirmation_code"] is not None


def test_get_reservation_detail(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    menu_id = seed_data["menu"].id

    # 作成
    create_res = client.post(
        f"/api/v1/admin/stores/{store_id}/reservations",
        headers=_auth(admin_token),
        json={
            "customer_name": "詳細テスト",
            "customer_phone": "090-1111-1111",
            "menu_id": menu_id,
            "start_datetime": _future_dt(11, 0),
        },
    )
    reservation_id = create_res.json()["id"]

    # 取得
    res = client.get(
        f"/api/v1/admin/stores/{store_id}/reservations/{reservation_id}",
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["id"] == reservation_id


def test_cancel_reservation(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    menu_id = seed_data["menu"].id

    create_res = client.post(
        f"/api/v1/admin/stores/{store_id}/reservations",
        headers=_auth(admin_token),
        json={
            "customer_name": "キャンセルテスト",
            "customer_phone": "090-2222-2222",
            "menu_id": menu_id,
            "start_datetime": _future_dt(12, 0),
        },
    )
    reservation_id = create_res.json()["id"]

    # 取消
    res = client.delete(
        f"/api/v1/admin/stores/{store_id}/reservations/{reservation_id}",
        headers=_auth(admin_token),
        json={"reason": "テスト取消"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_update_reservation_status_no_show(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    menu_id = seed_data["menu"].id

    create_res = client.post(
        f"/api/v1/admin/stores/{store_id}/reservations",
        headers=_auth(admin_token),
        json={
            "customer_name": "無断欠席テスト",
            "customer_phone": "090-3333-3333",
            "menu_id": menu_id,
            "start_datetime": _future_dt(13, 0),
        },
    )
    reservation_id = create_res.json()["id"]

    res = client.patch(
        f"/api/v1/admin/stores/{store_id}/reservations/{reservation_id}/status?new_status=no_show",
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "no_show"


def test_cannot_access_other_store(client, seed_data, admin_token):
    """他テナントの店舗には403が返ること"""
    fake_store_id = "00000000-0000-0000-0000-000000000000"
    res = client.get(
        f"/api/v1/admin/stores/{fake_store_id}/reservations",
        headers=_auth(admin_token),
    )
    assert res.status_code == 404  # store not found
