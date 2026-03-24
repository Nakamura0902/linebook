from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from ..database import Base


class CalendarSyncLog(Base):
    __tablename__ = "calendar_sync_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False)
    sync_type: Mapped[Optional[str]] = mapped_column(String(30))   # push|pull|webhook
    direction: Mapped[Optional[str]] = mapped_column(String(20))   # to_gcal|from_gcal
    status: Mapped[Optional[str]] = mapped_column(String(20))      # success|failed|conflict
    events_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_store_created", "store_id", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.id"))
    store_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("stores.id"))
    actor_type: Mapped[Optional[str]] = mapped_column(String(20))    # admin|customer|system
    actor_id: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[Optional[str]] = mapped_column(String(100))       # reservation.create 等
    resource_type: Mapped[Optional[str]] = mapped_column(String(100))
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    before_data: Mapped[Optional[Dict]] = mapped_column(JSON)
    after_data: Mapped[Optional[Dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
