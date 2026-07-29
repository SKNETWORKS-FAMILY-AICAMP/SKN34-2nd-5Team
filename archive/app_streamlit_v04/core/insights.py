"""위험유형·근거·전략 규칙. shared.retention.insights 재노출 wrapper.

실제 구현은 shared/retention/insights.py로 옮겼다. Streamlit 화면과
database/load/seed_reference_data.py 등 기존 `from core.insights import ...`
경로는 계속 이 파일을 통해 동작한다.
"""
from __future__ import annotations

from shared.retention.insights import (
    DECISION_PLAYBOOKS,
    DECISION_STATE_MAP,
    SIGNAL_LABELS,
    STATE_RECOMMENDATIONS,
    STRATEGIES,
    Signal,
    classify_risk_type,
    enrich_profiles,
    risk_signals,
    strategy_for,
)

__all__ = [
    "DECISION_PLAYBOOKS",
    "DECISION_STATE_MAP",
    "SIGNAL_LABELS",
    "STATE_RECOMMENDATIONS",
    "STRATEGIES",
    "Signal",
    "classify_risk_type",
    "enrich_profiles",
    "risk_signals",
    "strategy_for",
]
