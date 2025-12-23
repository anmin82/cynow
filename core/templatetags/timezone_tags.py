from __future__ import annotations

from datetime import timezone as dt_timezone
from typing import Any

from django import template
from django.utils import timezone

register = template.Library()


@register.filter(name="kst")
def kst(value: Any):
    """
    화면 표시용 KST 변환 필터.
    - aware datetime: Asia/Seoul로 변환
    - naive datetime: DB/ETL에서 UTC로 들어온 값으로 간주하고 UTC aware로 만든 뒤 KST로 변환
    - 그 외(None 등): 그대로 반환
    """
    if value is None:
        return None

    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day") and hasattr(value, "hour"):
        # datetime-like
        dt = value
        try:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, dt_timezone.utc)
            return timezone.localtime(dt, timezone.get_fixed_timezone(9 * 60))
        except Exception:
            return value

    return value


