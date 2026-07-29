"""숫자·문구 포맷 함수. shared.retention.formatters 재노출 wrapper.

실제 구현은 shared/retention/formatters.py로 옮겼다 — 위험유형·근거·전략
규칙과 마찬가지로 서식 함수도 한 곳에만 존재해야, Streamlit·API·export
스크립트가 서로 다른 결과를 내는 걸 막을 수 있다.
"""
from __future__ import annotations

from shared.retention.formatters import (
    compact_user_id,
    days,
    integer,
    is_missing,
    number,
    percent,
    safe_float,
    score,
    signed_phrase,
    signed_tone,
)

__all__ = [
    "compact_user_id",
    "days",
    "integer",
    "is_missing",
    "number",
    "percent",
    "safe_float",
    "score",
    "signed_phrase",
    "signed_tone",
]
