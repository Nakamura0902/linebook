import pytest


def test_login_success(client, seed_data):
    res = client.post("/api/v1/admin/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "super_admin"


def test_login_wrong_password(client, seed_data):
    res = client.post("/api/v1/admin/auth/login", json={
        "email": "test@example.com",
        "password": "wrong",
    })
    assert res.status_code == 401


def test_login_wrong_email(client, seed_data):
    res = client.post("/api/v1/admin/auth/login", json={
        "email": "notexist@example.com",
        "password": "password123",
    })
    assert res.status_code == 401


def test_get_me(client, seed_data, admin_token):
    res = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"


def test_get_me_without_token(client):
    res = client.get("/api/v1/admin/auth/me")
    assert res.status_code == 403  # HTTPBearerは403を返す


def test_get_me_invalid_token(client):
    res = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert res.status_code == 401
