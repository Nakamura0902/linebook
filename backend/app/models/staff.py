from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from ..database import Base


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_kana: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[Optional[str]] = mapped_column(String(100))
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    bio: Mapped[Optional[str]] = mapped_column(String(1000))
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_assignable: Mapped[bool] = mapped_column(Boolean, default=True)
    google_calendar_id: Mapped[Optional[str]] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    extra_data: Mapped[Dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    store: Mapped["Store"] = relationship("Store", back_populates="staff")
    menu_settings: Mapped[List["StaffMenuSettings"]] = relationship("StaffMenuSettings", back_populates="staff", cascade="all, delete-orphan")
    reservations: Mapped[List["Reservation"]] = relationship("Reservation", back_populates="staff")


class StaffMenuSettings(Base):
    __tablename__ = "staff_menu_settings"
    __table_args__ = (UniqueConstraint("staff_id", "menu_id", name="uq_staff_menu"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    staff_id: Mapped[str] = mapped_column(String(36), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    menu_id: Mapped[str] = mapped_column(String(36), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    staff: Mapped["Staff"] = relationship("Staff", back_populates="menu_settings")
    menu: Mapped["Menu"] = relationship("Menu", back_populates="staff_settings")
