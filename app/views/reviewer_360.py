from __future__ import annotations

import pandas as pd
import streamlit as st

from core.charts import interval_comparison, monthly_activity, profile_activity
from core.components import (
    action_rail,
    change_story,
    empty_state,
    evidence_list,
    footer,
    future_integration,
    profile_header,
    render_warnings,
    section_header,
)
from core.data import load_app_data
from core.insights import risk_signals, strategy_for


data = load_app_data()
profiles = data.reviewer_profiles

selected_user = st.session_state.get("selected_reviewer_id")
if selected_user not in set(profiles["user_id"].astype(str)):
    selected_user = str(profiles.iloc[0]["user_id"])
    st.session_state["selected_reviewer_id"] = selected_user

row = profiles.loc[profiles["user_id"].astype(str).eq(selected_user)].iloc[0]
strategy = strategy_for(row)
signals = risk_signals(row)

with st.container(horizontal=True, horizontal_alignment="distribute"):
    if st.button(
        "리뷰어 관리",
        icon=":material/arrow_back:",
        key="back_to_queue",
    ):
        st.session_state["reviewer_workspace_mode"] = "list"
        st.session_state["_returning_to_reviewer_queue"] = True
        st.query_params.clear()
        st.rerun()
    validation_mode = st.toggle(
        "검증 정답 표시",
        key="validation_mode",
        help="운영 시점에는 알 수 없었던 사후 결과를 검증 목적으로만 표시합니다.",
    )

profile_header(
    user_id=str(row["user_id"]),
    rank=int(row["risk_rank"]),
    score=float(row["risk_score"]),
    tier=str(row["risk_tier"]),
    selection_year=int(row["selection_year"]),
    target_year=int(row["target_year"]),
)
render_warnings(data.warnings)

main_column, action_column = st.columns([1.72, 0.58], gap="large")
with main_column:
    section_header(
        "활동이 이렇게 변했습니다",
        "선정 기간과 관찰 기간을 같은 기준으로 비교했습니다.",
        "현재 사용 가능",
    )
    change_story(
        [
            {
                "label": "리뷰 수",
                "before": f"{int(row['baseline_review_count'])}건",
                "after": f"{int(row['recent_review_count'])}건",
                "delta": f"{float(row['review_count_decline_rate']):.1%} 감소",
                "before_value": float(row["baseline_review_count"]),
                "after_value": float(row["recent_review_count"]),
                "icon": "rate_review",
            },
            {
                "label": "활동 월",
                "before": f"{int(row['baseline_active_months'])}개월",
                "after": f"{int(row['recent_active_months'])}개월",
                "delta": f"{float(row['active_month_decline_rate']):.1%} 감소",
                "before_value": float(row["baseline_active_months"]),
                "after_value": float(row["recent_active_months"]),
                "icon": "calendar_month",
            },
            {
                "label": "고유 음식점",
                "before": f"{int(row['baseline_unique_business_count'])}곳",
                "after": f"{int(row['recent_unique_business_count'])}곳",
                "delta": f"{float(row['unique_business_decline_rate']):.1%} 감소",
                "before_value": float(row["baseline_unique_business_count"]),
                "after_value": float(row["recent_unique_business_count"]),
                "icon": "location_on",
            },
            {
                "label": "리뷰 공백",
                "before": f"{float(row['baseline_recency_days']):.0f}일",
                "after": f"{float(row['recent_recency_days']):.0f}일",
                "delta": f"{float(row['recency_increase_days']):+.0f}일",
                "before_value": float(row["baseline_recency_days"]),
                "after_value": float(row["recent_recency_days"]),
                "icon": "hourglass_empty",
            },
        ]
    )

    evidence_column, chart_column = st.columns([0.82, 1.18], gap="large")
    with evidence_column:
        section_header(
            "왜 우선 검토 대상인가",
            "관찰 가능한 근거를 강한 순서로 정리했습니다.",
            "규칙 기반 프로토타입",
        )
        evidence_list(
            [(signal.name, signal.evidence, signal.group) for signal in signals[:3]]
        )
    with chart_column:
        section_header("활동 변화 요약", "과거와 최근 구간을 직접 비교합니다.")
        st.plotly_chart(
            profile_activity(row),
            width="stretch",
            key="reviewer_activity_chart",
        )

    detail_view = st.segmented_control(
        "상세 보기",
        ["활동 변화", "월별 타임라인", "사후 검증"],
        default="활동 변화",
        key="reviewer_detail_view",
        width="stretch",
    )

    if detail_view == "활동 변화":
        st.plotly_chart(
            interval_comparison(row),
            width="stretch",
            key="reviewer_interval_chart",
        )
    elif detail_view == "월별 타임라인":
        monthly = data.reviewer_monthly_activity
        user_monthly = (
            monthly.loc[monthly["user_id"].astype(str).eq(str(row["user_id"]))]
            if not monthly.empty and "user_id" in monthly.columns
            else pd.DataFrame()
        )
        if user_monthly.empty:
            empty_state(
                "월별 활동 타임라인",
                "활동 감소 시작점과 회복 여부를 표시할 제품 영역입니다.",
                "데이터 연결 필요",
                [
                    ("필요 데이터", "리뷰 작성 월, 월별 리뷰 수, 월별 고유 음식점 수"),
                    (
                        "활성화 조건",
                        "reviewer_monthly_activity_v01.parquet 계약 검증 완료",
                    ),
                ],
            )
        else:
            st.plotly_chart(
                monthly_activity(user_monthly),
                width="stretch",
                key="reviewer_monthly_chart",
            )
    elif validation_mode:
        st.info(
            "사후 검증 결과입니다. 운영 당시에는 알 수 없었던 정보이므로 "
            "예측 근거와 분리해 표시합니다.",
            icon=":material/visibility:",
        )
        truth_cols = st.columns(3, gap="large")
        with truth_cols[0]:
            st.metric("검증 기준", int(row["target_year"]))
        with truth_cols[1]:
            st.metric("실제 결과", str(row.get("actual_result", "—")))
        with truth_cols[2]:
            st.metric("사용 목적", "모델 검증 전용")
    else:
        empty_state(
            "사후 검증 결과가 숨겨져 있습니다",
            "화면 상단의 검증 정답 표시를 켜야 실제 결과를 확인할 수 있습니다.",
            "현재 사용 가능",
        )

with action_column:
    action_rail(
        title=strategy["primary"],
        description=strategy["summary"],
        steps=[
            ("1차 개입", strategy["primary"]),
            ("보조 개입", strategy["secondary"]),
            ("권장 채널", strategy["channel"]),
        ],
    )
    if st.button(
        "플레이북 적용 준비",
        type="primary",
        icon=":material/arrow_forward:",
        width="stretch",
        key="open_playbook",
    ):
        st.switch_page("views/playbook.py")
    future_integration(
        "CRM 캠페인 배정",
        "개입 일자, 담당자, 채널, 참여 및 복귀 결과",
    )

footer(data.data_mode)
