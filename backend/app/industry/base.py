from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AvailabilityRequest:
    store_id: str
    date: str                          # YYYY-MM-DD
    menu_id: Optional[str] = None
    staff_id: Optional[str] = None    # None = どのスタッフでもよい


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    staff_id: Optional[str]
    staff_name: Optional[str]
    is_available: bool = True


@dataclass
class BookingValidationResult:
    is_valid: bool
    error_message: Optional[str] = None


class IndustryTemplate(ABC):
    """
    業種別テンプレートの抽象基底クラス。
    新業種を追加する際はこのクラスを継承し、必要なメソッドをオーバーライドする。
    """

    @property
    @abstractmethod
    def industry_type(self) -> str:
        """業種識別子 e.g. 'beauty_salon'"""

    @abstractmethod
    def get_required_booking_fields(self, industry_config: dict) -> list[str]:
        """予約時の必須入力項目を返す"""

    @abstractmethod
    def get_optional_booking_fields(self, industry_config: dict) -> list[str]:
        """予約時の任意入力項目を返す"""

    @abstractmethod
    def validate_booking_request(
        self,
        booking_data: dict,
        industry_config: dict,
    ) -> BookingValidationResult:
        """業種固有の予約バリデーション"""

    @abstractmethod
    def calculate_end_time(
        self,
        start_datetime: datetime,
        menu_duration_minutes: int,
        buffer_minutes: int,
        staff_id: Optional[str],
        db_session,
    ) -> datetime:
        """終了時刻を計算する"""

    def get_default_industry_config(self) -> dict:
        """デフォルトのindustry_configを返す（DB初期値として使用）"""
        return {}
