"""
初期データ投入スクリプト。
使い方: python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import (
    Tenant, AdminUser, Store, StoreSettings, BusinessHours,
    Staff, MenuCategory, Menu, CancellationPolicy, NotificationTemplate,
    AdminStoreAccess,
)
from app.core.security import hash_password
from app.services.notification_service import get_default_templates
from app.industry.beauty_salon import BeautySalonTemplate
from datetime import time


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 既存データがあればスキップ
        if db.query(Tenant).first():
            print("Seed data already exists. Skipping.")
            return

        print("Seeding initial data...")

        # テナント作成（固定ID）
        tenant = Tenant(
            id="dcbc4ca3-baef-42e6-9742-b865ea99ea7a",
            name="サンプル美容室チェーン",
            slug="sample-salon",
        )
        db.add(tenant)
        db.flush()

        # 店舗作成（固定ID）
        store = Store(
            id="84a402b7-ba98-4f71-83da-5452247b835b",
            tenant_id=tenant.id,
            name="サンプル美容室 渋谷店",
            slug="shibuya",
            industry_type="beauty_salon",
            phone="03-1234-5678",
            address="東京都渋谷区○○ 1-2-3",
            line_channel_secret="ab23ccddbcfc223799e93dc1d3a9c805",
        )
        db.add(store)
        db.flush()

        # 管理者ユーザー作成
        admin = AdminUser(
            tenant_id=tenant.id,
            email="admin@example.com",
            password_hash=hash_password("password123"),
            name="管理者",
            role="super_admin",
        )
        db.add(admin)
        db.flush()

        # 管理者と店舗を紐づけ
        access = AdminStoreAccess(admin_user_id=admin.id, store_id=store.id)
        db.add(access)

        # 店舗設定
        template = BeautySalonTemplate()
        settings = StoreSettings(
            store_id=store.id,
            booking_mode="auto",
            slot_duration_minutes=30,
            advance_booking_days=60,
            min_booking_hours=1,
            reminder_enabled=True,
            reminder_send_time=time(9, 0),
            industry_config=template.get_default_industry_config(),
        )
        db.add(settings)

        # 営業時間（月〜土: 10:00-20:00、日: 休み）
        for dow in range(7):  # 0=日, 1=月, ..., 6=土
            is_open = dow != 0  # 日曜休み
            bh = BusinessHours(
                store_id=store.id,
                day_of_week=dow,
                is_open=is_open,
                open_time=time(10, 0) if is_open else None,
                close_time=time(20, 0) if is_open else None,
            )
            db.add(bh)

        # スタッフ
        staff_data = [
            {"name": "田中 花子", "role": "スタイリスト", "gender": "female", "sort_order": 1},
            {"name": "佐藤 太郎", "role": "スタイリスト", "gender": "male", "sort_order": 2},
            {"name": "鈴木 美咲", "role": "アシスタント", "gender": "female", "sort_order": 3},
        ]
        staff_list = []
        for d in staff_data:
            s = Staff(store_id=store.id, **d)
            db.add(s)
            staff_list.append(s)
        db.flush()

        # メニューカテゴリ
        cats = {}
        for name in ["カット", "カラー", "パーマ", "トリートメント"]:
            cat = MenuCategory(store_id=store.id, name=name)
            db.add(cat)
            cats[name] = cat
        db.flush()

        # メニュー
        menu_data = [
            {"name": "カット", "category": "カット", "duration_minutes": 60, "price": 5000},
            {"name": "カット＋シャンプー", "category": "カット", "duration_minutes": 90, "price": 6000},
            {"name": "フルカラー", "category": "カラー", "duration_minutes": 120, "price": 8000},
            {"name": "ハイライト", "category": "カラー", "duration_minutes": 150, "price": 12000},
            {"name": "デジタルパーマ", "category": "パーマ", "duration_minutes": 180, "price": 15000},
            {"name": "トリートメント", "category": "トリートメント", "duration_minutes": 60, "price": 3000},
        ]
        for i, d in enumerate(menu_data):
            cat_name = d.pop("category")
            m = Menu(store_id=store.id, category_id=cats[cat_name].id, sort_order=i, **d)
            db.add(m)

        # キャンセルポリシー
        policy = CancellationPolicy(
            store_id=store.id,
            name="標準キャンセルポリシー",
            is_default=True,
            cancel_deadline_hours=24,
            same_day_cancel_allowed=False,
            require_cancel_reason=False,
            description="ご予約の24時間前までキャンセル可能です。当日のキャンセルはご遠慮ください。",
        )
        db.add(policy)

        # デフォルト通知テンプレート
        for tmpl_data in get_default_templates(store.id):
            tmpl = NotificationTemplate(**tmpl_data)
            db.add(tmpl)

        db.commit()
        print(f"Seed complete!")
        print(f"  Tenant: {tenant.name} (id={tenant.id})")
        print(f"  Store: {store.name} (id={store.id})")
        print(f"  Admin: {admin.email} / password123")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
