# 業種別拡張ガイド

## 拡張方針

`industry/` ディレクトリに業種テンプレートを追加するだけで新業種をサポートできる。
DBスキーマは共通基盤を使い、業種固有の設定は `JSONB` カラムで吸収する。

## 新業種追加手順

### 1. テンプレートクラスを作成

```python
# backend/app/industry/restaurant.py

from .base import IndustryTemplate, BookingValidationResult

class RestaurantTemplate(IndustryTemplate):
    @property
    def industry_type(self) -> str:
        return "restaurant"

    def get_required_booking_fields(self, config: dict) -> list[str]:
        return ["name", "phone", "party_size"]

    def get_optional_booking_fields(self, config: dict) -> list[str]:
        return ["notes", "allergy"]

    def validate_booking_request(self, data: dict, config: dict) -> BookingValidationResult:
        party = data.get("extra_data", {}).get("party_size", 0)
        if party < 1 or party > 20:
            return BookingValidationResult(False, "人数が不正です")
        return BookingValidationResult(True)

    def calculate_end_time(self, start, duration, buffer, staff_id, db):
        from datetime import timedelta
        return start + timedelta(minutes=duration + buffer)

    def get_default_industry_config(self) -> dict:
        return {
            "availability_mode": "table_based",
            "max_party_size": 20,
            "required_fields": ["name", "phone", "party_size"],
            "optional_fields": ["notes", "allergy"],
        }
```

### 2. registryに登録

```python
# backend/app/industry/registry.py
from .restaurant import RestaurantTemplate

_register(RestaurantTemplate())
```

これだけで新業種が使えるようになる。

---

## 業種別差分整理

### 共通基盤（すべての業種で共通）

| 機能 | 説明 |
|---|---|
| テナント/店舗管理 | 変更不要 |
| 顧客管理 | extra_dataで拡張 |
| 予約CRUD | 変更不要 |
| 通知 | テンプレートで対応 |
| Gcal連携 | 変更不要 |
| 管理画面 | 大部分共通 |

### 飲食店（restaurant）

| 差分 | 内容 |
|---|---|
| 予約単位 | テーブル/席単位（staff概念なし or フロア担当） |
| 人数 | `extra_data.party_size` |
| スロット | 時間帯固定（17:00/18:00/19:00等） |
| 滞在時間 | 90〜120分固定 |
| DBスキーマ差分 | なし（extra_dataで吸収） |
| UI差分 | 人数選択UIを追加 |
| availability_mode | `table_based`（テーブル数をmax_booking_per_slotで管理） |

### 個人塾（cram_school）

| 差分 | 内容 |
|---|---|
| 顧客 | 生徒 + 保護者情報（extra_data） |
| スタッフ | 科目担当講師 |
| メニュー | 科目 + 授業時間 |
| 特殊設定 | 月謝制と都度払い混在（booking_modeで対応） |
| DBスキーマ差分 | customers.extra_dataに保護者情報 |

### クリニック（clinic）

| 差分 | 内容 |
|---|---|
| 予約種別 | 初診/再診フラグ強化 |
| 問診票 | `extra_data.questionnaire` (JSONB) |
| スタッフ | 診療科目別医師 |
| 予約確定 | 承認制推奨 |
| キャンセルポリシー | 厳格化 |
| セキュリティ | 医療情報の特別な取り扱い要検討 |

---

## 設定で吸収できるもの vs コード分岐が必要なもの

### 設定で吸収できるもの（industry_config JSONB）

- 必須/任意フィールドの切替
- スタッフ指名の有無
- スロット単位
- 最大予約人数
- 自動確定/承認制
- リマインド設定

### コード分岐が必要なもの（業種別テンプレートメソッド）

- 空き枠の計算方法（スタッフベース vs テーブルベース）
- 予約バリデーションロジック（人数チェック等）
- 終了時刻の計算（施術時間 vs 滞在時間）
- UI固有の入力項目
