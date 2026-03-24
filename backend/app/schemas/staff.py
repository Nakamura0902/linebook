from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StaffCreateRequest(BaseModel):
    name: str
    name_kana: Optional[str] = None
    role: Optional[str] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    image_url: Optional[str] = None
    is_assignable: bool = True
    google_calendar_id: Optional[str] = None
    sort_order: int = 0


class StaffUpdateRequest(BaseModel):
    name: Optional[str] = None
    name_kana: Optional[str] = None
    role: Optional[str] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_assignable: Optional[bool] = None
    google_calendar_id: Optional[str] = None
    sort_order: Optional[int] = None


class StaffMenuSettingItem(BaseModel):
    menu_id: str
    is_available: bool = True
    custom_duration_minutes: Optional[int] = None


class StaffMenuSettingsUpdateRequest(BaseModel):
    settings: list[StaffMenuSettingItem]


class StaffResponse(BaseModel):
    id: str
    store_id: str
    name: str
    name_kana: Optional[str]
    role: Optional[str]
    gender: Optional[str]
    bio: Optional[str]
    image_url: Optional[str]
    is_active: bool
    is_assignable: bool
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}
