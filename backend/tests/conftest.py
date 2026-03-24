import pytest
from datetime import datetime, timezone, time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import (
    Tenant, AdminUser, Store, StoreSettings, BusinessHours,
    Staff, Menu, MenuCategory, Customer, CancellationPolicy,
    NotificationTemplate, AdminStoreAccess,
)
from app.core.security import hash_password
from app.services.notification_service import get_default_templates

# テスト用インメモリSQLite
TEST_DB_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    conn = engine.connect()
    trans = conn.begin()
    session = TestingSessionLocal(bind=conn)
    yield session
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db):
    """基本シードデータを作成してdictで返す"""
    tenant = Tenant(name="テストチェーン", slug="test-chain")
    db.add(tenant)
    db.flush()

    store = Store(
        tenant_id=tenant.id,
        name="テスト店",
        slug="test",
        industry_type="beauty_salon",
    )
    db.add(store)
    db.flush()

    admin = AdminUser(
        tenant_id=tenant.id,
        email="test@example.com",
        password_hash=hash_password("password123"),
        name="テスト管理者",
        role="super_admin",
    )
    db.add(admin)
    db.flush()

    access = AdminStoreAccess(admin_user_id=admin.id, store_id=store.id)
    db.add(access)

    settings = StoreSettings(
        store_id=store.id,
        booking_mode="auto",
        slot_duration_minutes=30,
        advance_booking_days=60,
        min_booking_hours=0,  # テスト用: 0時間前でも可
    )
    db.add(settings)

    # 月〜土: 10:00-20:00
    for dow in range(7):
        is_open = dow != 0
        bh = BusinessHours(
            store_id=store.id,
            day_of_week=dow,
            is_open=is_open,
            open_time=time(10, 0) if is_open else None,
            close_time=time(20, 0) if is_open else None,
        )
        db.add(bh)

    staff = Staff(
        store_id=store.id,
        name="テストスタッフ",
        is_active=True,
        is_assignable=True,
    )
    db.add(staff)
    db.flush()

    cat = MenuCategory(store_id=store.id, name="カット")
    db.add(cat)
    db.flush()

    menu = Menu(
        store_id=store.id,
        category_id=cat.id,
        name="テストカット",
        duration_minutes=60,
        buffer_minutes=0,
        price=5000,
        is_active=True,
    )
    db.add(menu)

    policy = CancellationPolicy(
        store_id=store.id,
        name="テストポリシー",
        is_default=True,
        cancel_deadline_hours=None,  # 無制限
        same_day_cancel_allowed=True,
    )
    db.add(policy)

    for t in get_default_templates(store.id):
        db.add(NotificationTemplate(**t))

    customer = Customer(
        store_id=store.id,
        line_user_id="Utest12345",
        name="テスト顧客",
        phone="090-0000-0000",
        is_first_visit=True,
    )
    db.add(customer)

    db.flush()

    return {
        "tenant": tenant,
        "store": store,
        "admin": admin,
        "staff": staff,
        "menu": menu,
        "customer": customer,
        "policy": policy,
    }


@pytest.fixture
def admin_token(client, seed_data):
    res = client.post("/api/v1/admin/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    return res.json()["access_token"]
