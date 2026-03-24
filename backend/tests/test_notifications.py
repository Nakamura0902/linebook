"""
通知処理テスト。
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from app.services.notification_service import _render_template, _build_template_vars


def test_render_template_basic():
    """テンプレート変数が正しく置換されること"""
    template = "{{customer_name}}様、{{reservation_date}} {{reservation_time}}にご予約いただきました。"
    variables = {
        "customer_name": "山田花子",
        "reservation_date": "2024年4月1日",
        "reservation_time": "14:00",
    }
    result = _render_template(template, variables)
    assert result == "山田花子様、2024年4月1日 14:00にご予約いただきました。"


def test_render_template_missing_variable():
    """未定義変数はそのまま残ること"""
    template = "{{undefined_var}}のテスト"
    result = _render_template(template, {})
    assert "{{undefined_var}}" in result


def test_render_template_no_variables():
    """変数なしテンプレートはそのまま返ること"""
    template = "変数なしのテキストです"
    result = _render_template(template, {})
    assert result == "変数なしのテキストです"


@pytest.mark.asyncio
async def test_send_notification_no_template(db, seed_data):
    """テンプレートが未設定の場合は送信されないこと"""
    from app.services.notification_service import send_notification
    from app.models.reservation import Reservation
    from app.models.customer import Customer
    from app.models.notification import NotificationTemplate

    store = seed_data["store"]
    customer = seed_data["customer"]
    menu = seed_data["menu"]

    # 存在しないタイプのテンプレートで呼ぶ
    reservation = Reservation(
        store_id=store.id,
        customer_id=customer.id,
        menu_id=menu.id,
        status="confirmed",
        start_datetime=datetime.now(timezone.utc) + timedelta(days=3),
        end_datetime=datetime.now(timezone.utc) + timedelta(days=3, hours=1),
        confirmation_code="TEST0001",
    )
    db.add(reservation)
    db.flush()

    # 存在しないタイプ → Falseが返ること
    result = await send_notification(db, reservation, "nonexistent_type", store)
    assert result is False


@pytest.mark.asyncio
async def test_send_notification_no_line_token(db, seed_data):
    """LINE Tokenが未設定の場合は送信失敗ログが記録されること"""
    from app.services.notification_service import send_notification
    from app.models.reservation import Reservation
    from app.models.notification import NotificationLog

    store = seed_data["store"]
    customer = seed_data["customer"]
    menu = seed_data["menu"]

    # access_tokenなし
    assert store.line_access_token is None

    reservation = Reservation(
        store_id=store.id,
        customer_id=customer.id,
        menu_id=menu.id,
        status="confirmed",
        start_datetime=datetime.now(timezone.utc) + timedelta(days=3),
        end_datetime=datetime.now(timezone.utc) + timedelta(days=3, hours=1),
        confirmation_code="TEST0002",
    )
    db.add(reservation)
    db.flush()

    result = await send_notification(db, reservation, "booking_confirmed", store)
    assert result is False

    # 失敗ログが記録されていること
    log = db.query(NotificationLog).filter(
        NotificationLog.reservation_id == reservation.id,
        NotificationLog.status == "failed",
    ).first()
    assert log is not None
    assert "not configured" in (log.error_message or "")
