from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict
from sqlalchemy import String, Boolean, DateTime, Integer, Date, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from ..database import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("store_id", "line_user_id", name="uq_customer_store_line"),
        Index("idx_customers_store_line", "store_id", "line_user_id"),
        Index("idx_customers_store", "store_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    line_user_id: Mapped[Optional[str]] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    name_kana: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[str]] = mapped_column(String(10))  # male|female|other
    birthday: Mapped[Optional[date]] = mapped_column(Date)
    is_first_visit: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[Optional[str]] = mapped_column(String(500))
    memo: Mapped[Optional[str]] = mapped_column(String(2000))
    tags: Mapped[List] = mapped_column(JSON, default=list)
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_visit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancel_count: Mapped[int] = mapped_column(Integer, default=0)
    no_show_count: Mapped[int] = mapped_column(Integer, default=0)
    extra_data: Mapped[Dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    store: Mapped["Store"] = relationship("Store", back_populates="customers")
    reservations: Mapped[List["Reservation"]] = relationship("Reservation", back_populates="customer")
