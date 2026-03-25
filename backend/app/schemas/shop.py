from __future__ import annotations
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class ShopCategoryCreate(BaseModel):
    name: str
    emoji: Optional[str] = None
    sort_order: int = 0


class ShopCategoryResponse(BaseModel):
    id: str
    name: str
    emoji: Optional[str] = None
    sort_order: int

    model_config = {"from_attributes": True}


class ShopProductCreate(BaseModel):
    name: str
    category_id: Optional[str] = None
    description: Optional[str] = None
    staff_comment: Optional[str] = None
    price: Optional[int] = None
    image_url: Optional[str] = None
    external_url: str
    ec_platform: Optional[str] = None
    sort_order: int = 0


class ShopProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[str] = None
    description: Optional[str] = None
    staff_comment: Optional[str] = None
    price: Optional[int] = None
    image_url: Optional[str] = None
    external_url: Optional[str] = None
    ec_platform: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ShopProductResponse(BaseModel):
    id: str
    name: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    description: Optional[str] = None
    staff_comment: Optional[str] = None
    price: Optional[int] = None
    image_url: Optional[str] = None
    external_url: str
    ec_platform: Optional[str] = None
    is_active: bool
    sort_order: int
    click_count: int

    model_config = {"from_attributes": True}


class CustomerInterestSave(BaseModel):
    category_ids: list[str]
