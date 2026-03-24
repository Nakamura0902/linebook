from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from ..database import Base


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        Index(
            "idx_reservations_store_time",
            "store_id", "start_datetime", "end_datetime",
        ),
        Index(
            "idx_reservations_staff_time",
            "staff_id", "start_datetime", "end_datetime",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    staff_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("staff.id"))
    menu_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("menus.id"))
    # pending=仮予約, confirmed=確定, completed=完了, cancelled=取消, no_show=無断キャンセル
    status: Mapped[str] = mapped_column(String(30), default="confirmed", nullable=False)
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)          # ユーザー備考
    staff_notes: Mapped[Optional[str]] = mapped_column(Text)    # スタッフ内部メモ
    is_first_visit: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_proxy: Mapped[bool] = mapped_column(Boolean, default=False)  # 電話代理登録
    proxy_registered_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("admin_users.id"))
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(500))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_by_type: Mapped[Optional[str]] = mapped_column(String(20))  # customer|admin|system
    cancelled_by_id: Mapped[Optional[str]] = mapped_column(String(255))
    google_event_id: Mapped[Optional[str]] = mapped_column(String(255))
    confirmation_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    extra_data: Mapped[Dict] = mapped_column(JSON, default=dict)  # アレルギー等
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    store: Mapped["Store"] = relationship("Store", back_populates="reservations")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="reservations")
    staff: Mapped[Optional["Staff"]] = relationship("Staff", back_populates="reservations")
    menu: Mapped[Optional["Menu"]] = relationship("Menu")
    history: Mapped[List["ReservationHistory"]] = relationship("ReservationHistory", back_populates="reservation", cascade="all, delete-orphan")


class ReservationHistory(Base):
    __tablename__ = "reservation_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reservation_id: Mapped[str] = mapped_column(String(36), ForeignKey("reservations.id"), nullable=False)
    changed_by_type: Mapped[Optional[str]] = mapped_column(String(20))  # customer|admin|system
    changed_by_id: Mapped[Optional[str]] = mapped_column(String(255))
    # created|updated|cancelled|status_changed
    change_type: Mapped[Optional[str]] = mapped_column(String(30))
    before_data: Mapped[Optional[Dict]] = mapped_column(JSON)
    after_data: Mapped[Optional[Dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reservation: Mapped["Reservation"] = relationship("Reservation", back_populates="history")
