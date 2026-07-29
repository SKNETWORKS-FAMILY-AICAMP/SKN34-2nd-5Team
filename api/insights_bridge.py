"""shared.retention.insights / shared.retention.formatters 재노출.

위험유형·근거·전략 판단 규칙은 shared/retention/insights.py 하나에만
존재한다. 이전에는 archive/app_streamlit_v04를 sys.path에 얹어
core.insights를 import했는데, 그 경로는 core.data(streamlit)를 우회로
끌고 들어올 여지가 있어 shared를 직접 import하는 것으로 바꿨다. API는
이제 archive/를 전혀 건드리지 않는다.
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
from shared.retention.formatters import days, percent, signed_phrase

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
    "days",
    "percent",
    "signed_phrase",
]
