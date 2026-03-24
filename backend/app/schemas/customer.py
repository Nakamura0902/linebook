from __future__ import annotations
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, date
from typing import Optional


class CustomerUpdateRequest(BaseModel):
    name: Optional[str] = None
    name_kana: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[date] = None
    memo: Optional[str] = None
    tags: Optional[list[str]] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v:
            # 数字・ハイフン・括弧のみ許可
            import re
            if not re.match(r"^[\d\-\(\)\+\s]+$", v):
                raise ValueError("Invalid phone format")
            return v[:20]
        return v

    @field_validator("memo")
    @classmethod
    def limit_memo(cls, v):
        return v[:2000] if v else v


class BlacklistRequest(BaseModel):
    is_blacklisted: bool
    reason: Optional[str] = None


class CustomerResponse(BaseModel):
    id: str
    store_id: str
    line_user_id: Optional[str]
    name: Optional[str]
    name_kana: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    gender: Optional[str]
    birthday: Optional[date]
    is_first_visit: bool
    is_blacklisted: bool
    blacklist_reason: Optional[str]
    memo: Optional[str]
    tags: list
    visit_count: int
    last_visit_at: Optional[datetime]
    cancel_count: int
    no_show_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
