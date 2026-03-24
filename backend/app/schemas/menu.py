from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MenuCategoryCreateRequest(BaseModel):
    name: str
    sort_order: int = 0


class MenuCreateRequest(BaseModel):
    category_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    duration_minutes: int
    buffer_minutes: int = 0
    price: Optional[int] = None
    is_first_visit_only: bool = False
    is_revisit_only: bool = False
    booking_mode: str = "inherit"
    cancellation_policy_id: Optional[str] = None
    sort_order: int = 0
    extra_data: dict = {}


class MenuUpdateRequest(BaseModel):
    category_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    buffer_minutes: Optional[int] = None
    price: Optional[int] = None
    is_active: Optional[bool] = None
    is_first_visit_only: Optional[bool] = None
    is_revisit_only: Optional[bool] = None
    booking_mode: Optional[str] = None
    cancellation_policy_id: Optional[str] = None
    sort_order: Optional[int] = None
    extra_data: Optional[dict] = None


class MenuResponse(BaseModel):
    id: str
    store_id: str
    category_id: Optional[str]
    name: str
    description: Optional[str]
    duration_minutes: int
    buffer_minutes: int
    price: Optional[int]
    is_active: bool
    is_first_visit_only: bool
    is_revisit_only: bool
    booking_mode: str
    sort_order: int
    extra_data: dict
    created_at: datetime
    category_name: Optional[str] = None

    model_config = {"from_attributes": True}
