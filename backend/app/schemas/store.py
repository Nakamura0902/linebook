from __future__ import annotations
from pydantic import BaseModel
from datetime import time
from typing import Optional


class StoreSettingsUpdateRequest(BaseModel):
    booking_mode: Optional[str] = None
    slot_duration_minutes: Optional[int] = None
    advance_booking_days: Optional[int] = None
    min_booking_hours: Optional[int] = None
    reminder_enabled: Optional[bool] = None
    reminder_send_time: Optional[time] = None
    notify_admin_on_new: Optional[bool] = None
    notify_admin_on_cancel: Optional[bool] = None
    notify_admin_on_change: Optional[bool] = None
    industry_config: Optional[dict] = None


class BusinessHoursItem(BaseModel):
    day_of_week: int  # 0=日,1=月,...,6=土
    is_open: bool
    open_time: Optional[time] = None
    close_time: Optional[time] = None


class BusinessHoursUpdateRequest(BaseModel):
    hours: list[BusinessHoursItem]


class HolidayCreateRequest(BaseModel):
    date: str  # YYYY-MM-DD
    reason: Optional[str] = None


class BlockCreateRequest(BaseModel):
    staff_id: Optional[str] = None
    start_datetime: str  # ISO 8601
    end_datetime: str
    reason: Optional[str] = None


class CancellationPolicyCreateRequest(BaseModel):
    name: str
    is_default: bool = False
    cancel_deadline_hours: Optional[int] = None
    same_day_cancel_allowed: bool = True
    require_cancel_reason: bool = False
    description: Optional[str] = None


class NotificationTemplateUpdateRequest(BaseModel):
    type: str
    body: str
    is_active: bool = True


class StoreResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    industry_type: str
    phone: Optional[str]
    address: Optional[str]
    timezone: str
    is_active: bool
    liff_id: Optional[str]

    model_config = {"from_attributes": True}
