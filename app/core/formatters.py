from __future__ import annotations

import math
from typing import Any

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

