from __future__ import annotations

import math
from typing import Any, Callable

import pandas as pd


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def number(value: Any, digits: int = 0, suffix: str = "") -> str:
    if is_missing(value):
        return "—"
    numeric = float(value)
    if digits == 0:
        return f"{numeric:,.0f}{suffix}"
    return f"{numeric:,.{digits}f}{suffix}"


def integer(value: Any, suffix: str = "") -> str:
    return number(value, digits=0, suffix=suffix)


def percent(
    value: Any,
    digits: int = 1,
    *,
    already_percent: bool = False,
) -> str:
    if is_missing(value):
        return "—"
    numeric = float(value)
    if not already_percent:
        numeric *= 100
    return f"{numeric:.{digits}f}%"


def score(value: Any, digits: int = 3) -> str:
    if is_missing(value):
        return "—"
    return f"{float(value):.{digits}f}"


def days(value: Any, digits: int = 0) -> str:
    if is_missing(value):
        return "—"
    return f"{float(value):,.{digits}f}일"


def compact_user_id(value: Any, head: int = 7, tail: int = 5) -> str:
    text = str(value)
    if len(text) <= head + tail + 3:
        return text
    return f"{text[:head]}…{text[-tail:]}"


def safe_float(value: Any, default: float = 0.0) -> float:
    if is_missing(value):
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return default if not math.isfinite(numeric) else numeric


def signed_phrase(
    value: Any,
    formatter: Callable[[float], str],
    *,
    when_positive: str,
    when_negative: str,
) -> str:
    """Format `value` by magnitude and pick the word matching its actual sign.

    Metrics like decline rates can go negative (an actual increase), and a
    hardcoded "감소"/"증가" word would then contradict the sign.
    """
    numeric = safe_float(value)
    magnitude = formatter(abs(numeric))
    return f"{magnitude} {when_positive}" if numeric >= 0 else f"{magnitude} {when_negative}"


def signed_tone(value: Any, *, positive: str = "warning", negative: str = "positive") -> str:
    return positive if safe_float(value) >= 0 else negative

