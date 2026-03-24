from __future__ import annotations
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class ReservationCreateRequest(BaseModel):
    menu_id: str
    staff_id: Optional[str] = None
    start_datetime: datetime
    notes: Optional[str] = None
    is_first_visit: Optional[bool] = None
    extra_data: dict = {}
    # 顧客情報（初回登録時）
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_name_kana: Optional[str] = None

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v):
        if v:
            return v[:1000]  # 最大1000文字
        return v


class ReservationUpdateRequest(BaseModel):
    start_datetime: Optional[datetime] = None
    staff_id: Optional[str] = None
    notes: Optional[str] = None


class ReservationCancelRequest(BaseModel):
    reason: Optional[str] = None


class AdminReservationCreateRequest(BaseModel):
    """管理者による代理予約作成"""
    customer_id: Optional[str] = None
    # 顧客が未登録の場合
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None

    menu_id: str
    staff_id: Optional[str] = None
    start_datetime: datetime
    notes: Optional[str] = None
    staff_notes: Optional[str] = None
    is_first_visit: Optional[bool] = None
    extra_data: dict = {}


class ReservationResponse(BaseModel):
    id: str
    store_id: str
    customer_id: str
    staff_id: Optional[str]
    menu_id: Optional[str]
    status: str
    start_datetime: datetime
    end_datetime: datetime
    notes: Optional[str]
    staff_notes: Optional[str]
    is_first_visit: Optional[bool]
    is_proxy: bool
    cancellation_reason: Optional[str]
    cancelled_at: Optional[datetime]
    confirmation_code: Optional[str]
    extra_data: dict
    created_at: datetime

    # リレーション（オプション）
    staff_name: Optional[str] = None
    menu_name: Optional[str] = None
    customer_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AvailabilityRequest(BaseModel):
    date: str  # YYYY-MM-DD
    menu_id: str
    staff_id: Optional[str] = None


class TimeSlotResponse(BaseModel):
    start: datetime
    end: datetime
    staff_id: Optional[str]
    staff_name: Optional[str]
