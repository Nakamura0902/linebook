from __future__ import annotations
from .base import IndustryTemplate
from .beauty_salon import BeautySalonTemplate

_registry: dict[str, IndustryTemplate] = {}


def _register(template: IndustryTemplate) -> None:
    _registry[template.industry_type] = template


# 初期登録
_register(BeautySalonTemplate())


def get_template(industry_type: str) -> IndustryTemplate:
    """
    業種タイプからテンプレートインスタンスを取得する。
    未登録の業種は美容室テンプレートをフォールバックとして返す。
    新業種追加時はここに登録するだけでよい。
    """
    return _registry.get(industry_type, _registry["beauty_salon"])


def list_industry_types() -> list[str]:
    return list(_registry.keys())
