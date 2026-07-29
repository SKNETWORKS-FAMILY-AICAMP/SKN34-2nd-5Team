"""React JSON 계약 전용 표현 계층. 모델 규칙 자체는 아니다.

scripts/export_frontend_data.py의 `_f`/`_i`/`build_change_text`/`build_row`/
`build_detail` 원본이었으며, 그 파일은 이제 이 모듈을 import해서 쓴다.
Streamlit·DB·Parquet·CSV에 의존하지 않는다 — row(pandas.Series)만 받아서
JSON 직렬화 가능한 dict를 반환하는 순수 함수들이다.
"""
from __future__ import annotations

import pandas as pd

from shared.retention.formatters import days, percent, signed_phrase
from shared.retention.insights import DECISION_STATE_MAP, risk_signals, strategy_for


def _f(value, default: float = 0.0) -> float:
    """Coerce to a JSON-safe float (NaN/inf are not valid JSON)."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if pd.isna(numeric) or numeric in (float("inf"), float("-inf")):
        return default
    return numeric


def _i(value, default: int = 0) -> int:
    return int(_f(value, default))


def build_change_text(row: pd.Series) -> str:
    """Mirror the one-line "핵심 변화" summary in views/operation_home.py.

    The queue always phrases the change in review counts — picking whichever
    metric moved most would read better but would not match the Streamlit copy.
    """
    if not bool(row.get("prior_activity_available", 1)):
        comparison_year = _i(row.get("comparison_year"), 2017)
        return f"{comparison_year}년 비교 활동 없음 · 전년도 대비 변화율 계산 불가"

    return (
        f"리뷰 수 {_i(row.get('baseline_review_count'))}건 → "
        f"{_i(row.get('recent_review_count'))}건 · "
        + signed_phrase(
            row.get("review_count_decline_rate"),
            percent,
            when_positive="감소",
            when_negative="증가",
        )
    )


def build_row(row: pd.Series) -> dict:
    prior_available = bool(row.get("prior_activity_available", 1))
    comparison_year = _i(row.get("comparison_year"), 2017)
    no_comparison = f"{comparison_year}년 비교 활동 없음 · 전년도 대비 변화율 계산 불가"
    strategy = strategy_for(row)
    signals = risk_signals(row)

    def delta(value, formatter, positive: str, negative: str) -> str:
        if not prior_available:
            return no_comparison
        return signed_phrase(
            value, formatter, when_positive=positive, when_negative=negative
        )

    return {
        "userId": str(row["user_id"]),
        "sampleId": str(row["sample_id"]),
        "priorityRank": _i(row.get("priority_rank")),
        "priorityTopPercent": _f(row.get("priority_top_percent")),
        "priorityScore": _f(row.get("priority_score")),
        "modelJudgment": str(row.get("model_judgment", "")),
        "riskType": str(row.get("risk_type", "")),
        "coreSignal": str(row.get("core_signal", "")),
        "coreChange": build_change_text(row),
        "recommendedReview": strategy["primary"],
        "recommendedDecision": DECISION_STATE_MAP.get(
            _i(row.get("predicted_state")), "변화 지켜보기"
        ),
        "crmTarget": bool(row.get("crm_target", 0)),
        "crmTargetLabel": str(row.get("crm_target_label", "")),
        "priorActivityAvailable": prior_available,
        "comparisonYear": comparison_year,
        "selectionYear": _i(row.get("selection_year"), 2018),
        "targetYear": _i(row.get("target_year"), 2019),
        "scores": {
            "retained": _f(row.get("retained_score")),
            "weakened": _f(row.get("weakened_score")),
            "stopped": _f(row.get("stopped_score")),
        },
        "recentActiveMonths": _i(row.get("recent_active_months")),
        "recentRecencyDays": _f(row.get("recent_recency_days")),
        "reviewCountDeclineRate": _f(row.get("review_count_decline_rate")),
        "activeMonthDeclineRate": _f(row.get("active_month_decline_rate")),
        # The worklist "핵심 변화" column shows the 2 strongest signals
        # (views/risk_queue.py); the rest of the evidence lives in the detail file.
        "metrics": [signal.evidence for signal in signals[:2]],
    }


def build_detail(row: pd.Series) -> dict:
    """Fields only the Reviewer 360 screen needs, split out to keep the bundle small."""
    prior_available = bool(row.get("prior_activity_available", 1))
    comparison_year = _i(row.get("comparison_year"), 2017)
    no_comparison = f"{comparison_year}년 비교 활동 없음 · 전년도 대비 변화율 계산 불가"
    signals = risk_signals(row)

    def delta(value, formatter, positive: str, negative: str) -> str:
        if not prior_available:
            return no_comparison
        return signed_phrase(
            value, formatter, when_positive=positive, when_negative=negative
        )

    return {
        # "활동 변화 요약" grouped bar chart (Streamlit profile_activity)
        "activitySummary": [
            {
                "label": "리뷰 수",
                "before": _i(row.get("baseline_review_count")),
                "after": _i(row.get("recent_review_count")),
            },
            {
                "label": "활동 월",
                "before": _i(row.get("baseline_active_months")),
                "after": _i(row.get("recent_active_months")),
            },
            {
                "label": "고유 음식점",
                "before": _i(row.get("baseline_unique_business_count")),
                "after": _i(row.get("recent_unique_business_count")),
            },
        ],
        # "작성 주기 변화" chart (Streamlit interval_comparison)
        "intervalComparison": [
            {
                "label": "평균 작성 간격",
                "before": _f(row.get("baseline_mean_interval_days")),
                "after": _f(row.get("recent_mean_interval_days")),
            },
            {
                "label": "마지막 리뷰 공백",
                "before": _f(row.get("baseline_recency_days")),
                "after": _f(row.get("recent_recency_days")),
            },
        ],
        # "활동이 이렇게 변했습니다" tiles (Streamlit change_story)
        "changes": [
            {
                "label": "리뷰 수",
                "before": (
                    f"{_i(row.get('baseline_review_count'))}건"
                    if prior_available
                    else f"{comparison_year}년 비교 활동 없음"
                ),
                "after": f"{_i(row.get('recent_review_count'))}건",
                "delta": delta(
                    row.get("review_count_decline_rate"), percent, "감소", "증가"
                ),
                "tone": (
                    "muted"
                    if not prior_available
                    else (
                        "warning"
                        if _f(row.get("review_count_decline_rate")) >= 0
                        else "positive"
                    )
                ),
            },
            {
                "label": "활동 월",
                "before": (
                    f"{_i(row.get('baseline_active_months'))}개월"
                    if prior_available
                    else f"{comparison_year}년 비교 활동 없음"
                ),
                "after": f"{_i(row.get('recent_active_months'))}개월",
                "delta": delta(
                    row.get("active_month_decline_rate"), percent, "감소", "증가"
                ),
                "tone": (
                    "muted"
                    if not prior_available
                    else (
                        "warning"
                        if _f(row.get("active_month_decline_rate")) >= 0
                        else "positive"
                    )
                ),
            },
            {
                "label": "고유 음식점",
                "before": (
                    f"{_i(row.get('baseline_unique_business_count'))}곳"
                    if prior_available
                    else f"{comparison_year}년 비교 활동 없음"
                ),
                "after": f"{_i(row.get('recent_unique_business_count'))}곳",
                "delta": delta(
                    row.get("unique_business_decline_rate"), percent, "감소", "증가"
                ),
                "tone": (
                    "muted"
                    if not prior_available
                    else (
                        "warning"
                        if _f(row.get("unique_business_decline_rate")) >= 0
                        else "positive"
                    )
                ),
            },
            {
                "label": "리뷰 공백",
                "before": (
                    days(row.get("baseline_recency_days"))
                    if prior_available
                    else f"{comparison_year}년 비교 활동 없음"
                ),
                "after": days(row.get("recent_recency_days")),
                "delta": (
                    f"{_f(row.get('recency_increase_days')):+.0f}일"
                    if prior_available
                    else no_comparison
                ),
                "tone": (
                    "muted"
                    if not prior_available
                    else (
                        "positive"
                        if _f(row.get("recency_increase_days")) < 0
                        else "warning"
                    )
                ),
            },
        ],
        # Streamlit shows the 3 strongest signals, ordered by severity.
        "evidence": [
            {"title": signal.name, "evidence": signal.evidence, "group": signal.group}
            for signal in signals[:3]
        ],
        # strategy is a pure function of (predicted_state, risk_type); the two
        # lookup tables ship once in strategies.json rather than per reviewer.
        "predictedState": _i(row.get("predicted_state")),
        # Post-hoc validation, hidden behind the disclosure toggle in the UI.
        "actual": {
            "state": str(row.get("retention_state_label", "—")),
            "targetReviewCount": _i(row.get("target_review_count")),
            "targetActiveMonths": _i(row.get("target_active_months")),
        },
    }
