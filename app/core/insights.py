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

# predicted_state → 관리자 판단 기본 추천값. reviewer_360.py의 라디오 기본 선택값과
# 동일한 매핑을 리텐션 플레이북에서도 재사용하기 위해 여기서 한 번만 정의한다
# (DEC-011 §2.3 명칭 기준).
DECISION_STATE_MAP = {
    0: "변화 지켜보기",
    1: "리뷰 활동 늘리기",
    2: "리뷰 다시 시작 유도",
}

# 관리자 판단별 플레이북 초안 (DEC-011 §4). 개입 효과가 검증된 처방이 아니며
# 규칙 기반 운영 아이디어 초안이다. "success_draft"는 아직 측정 데이터가 없어
# 화면에 표시할 때 반드시 "고도화 예정"류 배지를 같이 달아야 한다.
DECISION_PLAYBOOKS = {
    "리뷰 다시 시작 유도": {
        "condition": "중단 우세 판단, 최근 리뷰 공백 장기화, 최근 활동 월·리뷰 수 급감",
        "signals": "마지막 리뷰 공백, 최근 리뷰 수, 활동 월, 탐색 활동 변화",
        "primary_action": "대상 적합성 확인 후 재참여 메시지 또는 개인 활동 리포트 제안 검토",
        "sub_strategy": {
            "작성 주기 이완형": "작성 재개 계기 중심",
            "복합 위험형": "운영자 검토 후 맞춤 제안",
        },
        "channel": "앱 내 메시지 우선 검토",
        "needs_upgrade": "이메일·푸시·혜택 제공에는 수신 동의·언어·채널 정보 필요",
        "success_draft": "일정 기간 내 리뷰 재개 여부, 활동 월 재발생 여부",
    },
    "리뷰 활동 늘리기": {
        "condition": "약화 우세 판단, 최근 활동은 있으나 리뷰 수·활동 월·탐색 활동이 감소",
        "signals": "리뷰 수 감소, 활동 월 감소, 작성 간격 증가, 고유 음식점 수 감소",
        "primary_action": "현재 관심사를 반영한 탐색·콘텐츠·리뷰 작성 계기 제안 검토",
        "sub_strategy": {
            "활동량 붕괴형": "리뷰 활동량 회복",
            "작성 주기 이완형": "루틴 회복",
            "탐색 활동 축소형": "신규 탐방 유도",
        },
        "channel": "운영자 검토 후 앱 내 메시지 또는 콘텐츠 노출",
        "needs_upgrade": "개인화 추천에는 선호 카테고리·지역·채널 데이터 필요",
        "success_draft": "다음 기간 리뷰 수·활동 월·고유 음식점 수 회복 여부",
    },
    "변화 지켜보기": {
        "condition": "유지 우세, 일반 모니터링, 일시적 감소 가능성, 활동 근거 부족",
        "signals": "최근 활동 재개 여부, 추가 약화 신호 발생 여부, 우선순위 변화",
        "primary_action": "캠페인 실행 없이 재검토 기준과 시점을 설정",
        "sub_strategy": {
            "일반 모니터링형": "일반 추천 또는 비개입 모니터링",
        },
        "channel": "즉시 실행 채널 없음",
        "needs_upgrade": "재검토 알림·담당자 배정",
        "success_draft": "재검토 시점에 유지·회복·추가 약화 여부",
    },
    "이번엔 제외": {
        "condition": "데이터 품질 문제, 최근 활동 회복 확인, 중복·오분류 가능성, 현재 운영 대상 외",
        "signals": "데이터 이상 여부, 최근 활동 변화, 제외 사유",
        "primary_action": "캠페인·메시지 미실행",
        "sub_strategy": {},
        "channel": "없음",
        "needs_upgrade": "제외 사유·담당자·재검토 시점의 영구 이력 저장",
        "success_draft": "제외 대상의 재편입 필요 여부 및 오분류 여부",
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
    prior_available = bool(_value(row, "prior_activity_available", 1))
    comparison_year = int(_value(row, "comparison_year", 2017))
    no_comparison = (
        f"{comparison_year}년 비교 활동 없음 · 전년도 대비 변화율 계산 불가"
    )
    recent_months = _value(row, "recent_active_months", 0)
    month_decline = _value(row, "active_month_decline_rate")
    review_decline = _value(row, "review_count_decline_rate")
    recent_reviews = _value(row, "recent_review_count")
    recency = _value(row, "recent_recency_days")
    recency_increase = _value(row, "recency_increase_days")
    interval_increase = _value(row, "mean_interval_increase_days")
    business_decline = _value(row, "unique_business_decline_rate")
    month_evidence = (
        f"최근 활동 {recent_months:.0f}개월 · 이전 대비 "
        f"{signed_phrase(month_decline, percent, when_positive='감소', when_negative='증가')}"
        if prior_available
        else f"최근 활동 {recent_months:.0f}개월 · {no_comparison}"
    )
    review_evidence = (
        f"최근 {recent_reviews:.0f}건 · 이전 대비 "
        f"{signed_phrase(review_decline, percent, when_positive='감소', when_negative='증가')}"
        if prior_available
        else f"최근 {recent_reviews:.0f}건 · {no_comparison}"
    )
    recency_comparison = (
        "이전 기간보다 "
        + signed_phrase(
            recency_increase,
            days,
            when_positive="증가",
            when_negative="감소",
        )
        if prior_available
        else f"{comparison_year}년 비교 활동 없음"
    )
    interval_evidence = (
        "평균 리뷰 간격이 "
        f"{signed_phrase(interval_increase, days, when_positive='증가', when_negative='감소')}"
        if prior_available
        else f"{comparison_year}년 비교 활동 없음 · 최근 작성 간격만 확인 가능"
    )
    business_evidence = (
        "고유 음식점 수가 "
        f"{signed_phrase(business_decline, percent, when_positive='감소', when_negative='증가')}"
        if prior_available
        else no_comparison
    )

    candidates.extend(
        [
            Signal(
                "최근 활동 지속성",
                month_evidence,
                max(month_decline, (6 - recent_months) / 6),
                "활동량",
            ),
            Signal(
                "리뷰 생산량",
                review_evidence,
                review_decline,
                "활동량",
            ),
            Signal(
                "마지막 리뷰 공백",
                " · ".join(
                    [f"최근 공백 {days(recency)}"]
                    + (["150일 기준선 초과"] if recency >= 150 else [])
                    + [recency_comparison]
                ),
                max(recency / 150, recency_increase / 90),
                "작성 간격",
            ),
            Signal(
                "평균 작성 간격",
                interval_evidence,
                interval_increase / 60,
                "작성 간격",
            ),
            Signal(
                "음식점 탐색량",
                business_evidence,
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
