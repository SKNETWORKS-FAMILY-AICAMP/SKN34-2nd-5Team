from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.formatters import days, percent, safe_float, signed_phrase


@dataclass(frozen=True)
class Signal:
    name: str
    evidence: str
    severity: float
    group: str


STRATEGIES = {
    "활동량 붕괴형": {
        "summary": "최근 활동 월과 리뷰 수가 함께 감소했습니다.",
        "primary": "짧은 리뷰 복귀 미션",
        "secondary": "개인 활동 리포트와 등급 유지 혜택 안내",
        "channel": "앱 내 메시지 · 이메일",
    },
    "작성 주기 이완형": {
        "summary": "마지막 리뷰 이후 공백과 작성 간격이 길어졌습니다.",
        "primary": "복귀 알림과 월간 리뷰 미션",
        "secondary": "저부담 사진·한줄 리뷰 형식 제안",
        "channel": "푸시 · 앱 내 메시지",
    },
    "탐색 활동 축소형": {
        "summary": "최근 방문한 고유 음식점 수가 크게 감소했습니다.",
        "primary": "미방문 맛집 탐색 미션",
        "secondary": "취향 기반 신규 음식점 컬렉션 제공",
        "channel": "추천 피드 · 앱 내 메시지",
    },
    "복합 위험형": {
        "summary": "여러 활동 신호가 동시에 약화되고 있습니다.",
        "primary": "개인 활동 리포트 기반 맞춤 복귀 제안",
        "secondary": "위험 신호를 확인한 뒤 운영자가 혜택 강도 결정",
        "channel": "운영자 검토 · 앱 내 메시지",
    },
    "일반 모니터링형": {
        "summary": "급격한 활동 붕괴 신호는 확인되지 않았습니다.",
        "primary": "일반 추천과 정기 활동 요약",
        "secondary": "추가 개입 없이 점수 변화 모니터링",
        "channel": "추천 피드",
    },
}

SIGNAL_LABELS = {
    "복합 위험형": "복합 약화 신호",
    "활동량 붕괴형": "리뷰·활동 월 감소",
    "작성 주기 이완형": "리뷰 공백 증가",
    "탐색 활동 축소형": "음식점 탐색 감소",
    "일반 모니터링형": "급격한 변화 없음",
}

STATE_RECOMMENDATIONS = {
    0: {
        "primary": "관찰 유지",
        "summary": "유지 점수가 우세합니다. 급격한 행동 변화가 있는지만 확인합니다.",
    },
    1: {
        "primary": "활동 회복 검토",
        "summary": "파워 지위 약화 점수가 우세합니다. 활동 지속성을 회복할 개입을 검토합니다.",
    },
    2: {
        "primary": "복귀·재활성화 검토",
        "summary": "리뷰 활동 중단 점수가 우세합니다. 장기 공백과 최근 활동을 확인한 뒤 복귀 전략을 검토합니다.",
    },
}


def _value(row: pd.Series, column: str, default: float = 0.0) -> float:
    return safe_float(row.get(column), default)


def classify_risk_type(row: pd.Series) -> str:
    in_review_queue = bool(row.get("crm_target", 0))
    review_decline = _value(row, "review_count_decline_rate")
    month_decline = _value(row, "active_month_decline_rate")
    recency_increase = _value(row, "recency_increase_days")
    interval_increase = _value(row, "mean_interval_increase_days")
    business_decline = _value(row, "unique_business_decline_rate")
    recent_months = _value(row, "recent_active_months", 12)

    activity_score = max(review_decline, month_decline) + (0.25 if recent_months <= 3 else 0)
    interval_score = max(recency_increase / 90, interval_increase / 60)
    exploration_score = business_decline

    maximum = max(activity_score, interval_score, exploration_score)
    strong_count = sum(
        value >= threshold
        for value, threshold in [
            (activity_score, 0.50),
            (interval_score, 0.45),
            (exploration_score, 0.50),
        ]
    )
    if strong_count >= 2:
        return "복합 위험형"
    if activity_score == maximum and activity_score >= 0.30:
        return "활동량 붕괴형"
    if interval_score == maximum and interval_score >= 0.25:
        return "작성 주기 이완형"
    if exploration_score == maximum and exploration_score >= 0.30:
        return "탐색 활동 축소형"
    if not in_review_queue:
        return "일반 모니터링형"
    return "복합 위험형"


def risk_signals(row: pd.Series) -> list[Signal]:
    candidates: list[Signal] = []
    recent_months = _value(row, "recent_active_months", 0)
    month_decline = _value(row, "active_month_decline_rate")
    review_decline = _value(row, "review_count_decline_rate")
    recent_reviews = _value(row, "recent_review_count")
    recency = _value(row, "recent_recency_days")
    recency_increase = _value(row, "recency_increase_days")
    interval_increase = _value(row, "mean_interval_increase_days")
    business_decline = _value(row, "unique_business_decline_rate")

    candidates.extend(
        [
            Signal(
                "최근 활동 지속성",
                f"최근 활동 {recent_months:.0f}개월 · 이전 대비 "
                f"{signed_phrase(month_decline, percent, when_positive='감소', when_negative='증가')}",
                max(month_decline, (6 - recent_months) / 6),
                "활동량",
            ),
            Signal(
                "리뷰 생산량",
                f"최근 {recent_reviews:.0f}건 · 이전 대비 "
                f"{signed_phrase(review_decline, percent, when_positive='감소', when_negative='증가')}",
                review_decline,
                "활동량",
            ),
            Signal(
                "마지막 리뷰 공백",
                " · ".join(
                    [f"최근 공백 {days(recency)}"]
                    + (["150일 기준선 초과"] if recency >= 150 else [])
                    + [
                        "이전 기간보다 "
                        + signed_phrase(
                            recency_increase, days,
                            when_positive='증가', when_negative='감소',
                        )
                    ]
                ),
                max(recency / 150, recency_increase / 90),
                "작성 간격",
            ),
            Signal(
                "평균 작성 간격",
                "평균 리뷰 간격이 "
                f"{signed_phrase(interval_increase, days, when_positive='증가', when_negative='감소')}",
                interval_increase / 60,
                "작성 간격",
            ),
            Signal(
                "음식점 탐색량",
                "고유 음식점 수가 "
                f"{signed_phrase(business_decline, percent, when_positive='감소', when_negative='증가')}",
                business_decline,
                "음식점 탐색",
            ),
        ]
    )
    return sorted(candidates, key=lambda signal: signal.severity, reverse=True)


def enrich_profiles(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    enriched = frame.copy()
    enriched["risk_type"] = enriched.apply(classify_risk_type, axis=1)
    enriched["recommended_action"] = enriched["risk_type"].map(
        lambda risk_type: STRATEGIES[risk_type]["primary"]
    )
    enriched["core_signal"] = enriched["risk_type"].map(SIGNAL_LABELS)
    if "predicted_state" in enriched.columns:
        enriched["recommended_review"] = enriched["predicted_state"].map(
            lambda state: STATE_RECOMMENDATIONS.get(
                int(state), STATE_RECOMMENDATIONS[0]
            )["primary"]
        )
    else:
        enriched["recommended_review"] = enriched["recommended_action"]
    return enriched


def strategy_for(row: pd.Series) -> dict[str, Any]:
    risk_type = str(row.get("risk_type") or classify_risk_type(row))
    strategy = {"risk_type": risk_type, **STRATEGIES[risk_type]}
    if "predicted_state" in row and not pd.isna(row.get("predicted_state")):
        state = int(row.get("predicted_state", 0))
        recommendation = STATE_RECOMMENDATIONS.get(state, STATE_RECOMMENDATIONS[0])
        strategy["primary"] = recommendation["primary"]
        strategy["summary"] = recommendation["summary"]
    return strategy
