from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from ..database import Base


class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    store: Mapped["Store"] = relationship("Store")
    menus: Mapped[List["Menu"]] = relationship("Menu", back_populates="category")


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("menu_categories.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_first_visit_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_revisit_only: Mapped[bool] = mapped_column(Boolean, default=False)
    # 'inherit'=店舗設定に従う | 'auto'=自動確定 | 'approval'=承認制
    booking_mode: Mapped[str] = mapped_column(String(20), default="inherit")
    cancellation_policy_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("cancellation_policies.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    extra_data: Mapped[Dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    store: Mapped["Store"] = relationship("Store", back_populates="menus")
    category: Mapped[Optional["MenuCategory"]] = relationship("MenuCategory", back_populates="menus")
    staff_settings: Mapped[List["StaffMenuSettings"]] = relationship("StaffMenuSettings", back_populates="menu", cascade="all, delete-orphan")
    cancellation_policy: Mapped[Optional["CancellationPolicy"]] = relationship("CancellationPolicy", foreign_keys=[cancellation_policy_id])
