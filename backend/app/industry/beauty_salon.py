from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from .base import IndustryTemplate, BookingValidationResult


class BeautySalonTemplate(IndustryTemplate):
    """
    美容室向けテンプレート。
    - スタッフ指名制
    - メニュー時間ベースの予約
    - 性別指定対応
    - 新規/再来フラグ
    """

    @property
    def industry_type(self) -> str:
        return "beauty_salon"

    def get_required_booking_fields(self, industry_config: dict) -> list[str]:
        base = ["name", "phone"]
        required = industry_config.get("required_fields", base)
        return required

    def get_optional_booking_fields(self, industry_config: dict) -> list[str]:
        base = ["name_kana", "email", "gender", "allergy_notes", "notes", "coupon_code"]
        return industry_config.get("optional_fields", base)

    def validate_booking_request(
        self,
        booking_data: dict,
        industry_config: dict,
    ) -> BookingValidationResult:
        required = self.get_required_booking_fields(industry_config)

        # 必須項目チェック
        customer_data = booking_data.get("customer", {})
        for field in required:
            if not customer_data.get(field):
                return BookingValidationResult(
                    is_valid=False,
                    error_message=f"必須項目が入力されていません: {field}",
                )

        # スタッフ指名が有効な場合、指名スタッフの性別制限チェック
        # （実際のスタッフ情報はDBから取得する必要があるため、ここでは基本チェックのみ）

        return BookingValidationResult(is_valid=True)

    def calculate_end_time(
        self,
        start_datetime: datetime,
        menu_duration_minutes: int,
        buffer_minutes: int,
        staff_id: Optional[str],
        db_session,
    ) -> datetime:
        """
        施術時間 + バッファ時間で終了時刻を計算。
        スタッフ固有の時間設定がある場合はそちらを優先。
        """
        actual_duration = menu_duration_minutes

        if staff_id and db_session:
            from ..models.staff import StaffMenuSettings
            # スタッフ固有の施術時間が設定されていれば使用
            # （menu_idは呼び出し元から渡される必要があるが、ここでは簡略化）

        return start_datetime + timedelta(minutes=actual_duration + buffer_minutes)

    def get_default_industry_config(self) -> dict:
        return {
            "staff_nomination_enabled": True,
            "allow_gender_preference": True,
            "new_customer_menus_only": False,
            "availability_mode": "staff_based",  # staff_based | store_based
            "required_fields": ["name", "phone"],
            "optional_fields": ["name_kana", "email", "gender", "allergy_notes", "notes", "coupon_code"],
        }
