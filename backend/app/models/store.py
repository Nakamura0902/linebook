from __future__ import annotations
import uuid
from datetime import datetime, time
from typing import Optional, List, Dict
from sqlalchemy import String, Boolean, DateTime, Integer, Time, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from ..database import Base


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_store_tenant_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    industry_type: Mapped[str] = mapped_column(String(50), default="beauty_salon")
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Tokyo")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # LINE設定
    line_channel_id: Mapped[Optional[str]] = mapped_column(String(100))
    line_channel_secret: Mapped[Optional[str]] = mapped_column(String(500))
    line_access_token: Mapped[Optional[str]] = mapped_column(String(500))
    liff_id: Mapped[Optional[str]] = mapped_column(String(100))
    # Google Calendar
    google_calendar_id: Mapped[Optional[str]] = mapped_column(String(255))
    google_refresh_token: Mapped[Optional[str]] = mapped_column(String(500))
    google_webhook_channel_id: Mapped[Optional[str]] = mapped_column(String(255))
    google_webhook_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="stores")
    settings: Mapped[Optional["StoreSettings"]] = relationship("StoreSettings", back_populates="store", uselist=False)
    staff: Mapped[List["Staff"]] = relationship("Staff", back_populates="store")
    menus: Mapped[List["Menu"]] = relationship("Menu", back_populates="store")
    customers: Mapped[List["Customer"]] = relationship("Customer", back_populates="store")
    reservations: Mapped[List["Reservation"]] = relationship("Reservation", back_populates="store")
    business_hours: Mapped[List["BusinessHours"]] = relationship("BusinessHours", back_populates="store")
    holidays: Mapped[List["Holiday"]] = relationship("Holiday", back_populates="store")
    reservation_blocks: Mapped[List["ReservationBlock"]] = relationship("ReservationBlock", back_populates="store")
    notification_templates: Mapped[List["NotificationTemplate"]] = relationship("NotificationTemplate", back_populates="store")
    cancellation_policies: Mapped[List["CancellationPolicy"]] = relationship("CancellationPolicy", back_populates="store")


class StoreSettings(Base):
    __tablename__ = "store_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), unique=True, nullable=False)
    booking_mode: Mapped[str] = mapped_column(String(20), default="auto")
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    advance_booking_days: Mapped[int] = mapped_column(Integer, default=60)
    min_booking_hours: Mapped[int] = mapped_column(Integer, default=1)
    max_booking_per_slot: Mapped[int] = mapped_column(Integer, default=1)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_send_time: Mapped[Optional[time]] = mapped_column(Time, default=time(9, 0))
    notify_admin_on_new: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_admin_on_cancel: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_admin_on_change: Mapped[bool] = mapped_column(Boolean, default=True)
    default_cancellation_policy_id: Mapped[Optional[str]] = mapped_column(String(36))
    industry_config: Mapped[Dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    store: Mapped["Store"] = relationship("Store", back_populates="settings")


class BusinessHours(Base):
    __tablename__ = "business_hours"
    __table_args__ = (UniqueConstraint("store_id", "day_of_week", name="uq_bh_store_day"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=日,1=月,...,6=土
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    open_time: Mapped[Optional[time]] = mapped_column(Time)
    close_time: Mapped[Optional[time]] = mapped_column(Time)

    store: Mapped["Store"] = relationship("Store", back_populates="business_hours")


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("store_id", "date", name="uq_holiday_store_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    reason: Mapped[Optional[str]] = mapped_column(String(255))

    store: Mapped["Store"] = relationship("Store", back_populates="holidays")


class ReservationBlock(Base):
    __tablename__ = "reservation_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    staff_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("staff.id"))
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255))
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    store: Mapped["Store"] = relationship("Store", back_populates="reservation_blocks")
