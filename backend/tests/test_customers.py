"""
顧客管理APIテスト。
"""
import pytest


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_list_customers(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    res = client.get(
        f"/api/v1/admin/stores/{store_id}/customers",
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1  # seedデータに1件あり
    assert any(c["name"] == "テスト顧客" for c in data["items"])


def test_search_customer_by_name(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    res = client.get(
        f"/api/v1/admin/stores/{store_id}/customers?search=テスト顧客",
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_search_customer_no_result(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    res = client.get(
        f"/api/v1/admin/stores/{store_id}/customers?search=存在しない顧客xyz",
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_get_customer_detail(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    customer_id = seed_data["customer"].id

    res = client.get(
        f"/api/v1/admin/stores/{store_id}/customers/{customer_id}",
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    data = res.json()
    assert "customer" in data
    assert "recent_reservations" in data


def test_update_customer_memo(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    customer_id = seed_data["customer"].id

    res = client.put(
        f"/api/v1/admin/stores/{store_id}/customers/{customer_id}",
        headers=_auth(admin_token),
        json={"memo": "テストメモ追加", "tags": ["VIP", "常連"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["memo"] == "テストメモ追加"
    assert "VIP" in data["tags"]


def test_blacklist_customer(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    customer_id = seed_data["customer"].id

    res = client.patch(
        f"/api/v1/admin/stores/{store_id}/customers/{customer_id}/blacklist",
        headers=_auth(admin_token),
        json={"is_blacklisted": True, "reason": "テスト理由"},
    )
    assert res.status_code == 200
    assert res.json()["is_blacklisted"] is True

    # 解除
    res2 = client.patch(
        f"/api/v1/admin/stores/{store_id}/customers/{customer_id}/blacklist",
        headers=_auth(admin_token),
        json={"is_blacklisted": False},
    )
    assert res2.status_code == 200
    assert res2.json()["is_blacklisted"] is False


def test_export_csv(client, seed_data, admin_token):
    store_id = seed_data["store"].id
    res = client.get(
        f"/api/v1/admin/stores/{store_id}/customers/export",
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "テスト顧客" in res.text
