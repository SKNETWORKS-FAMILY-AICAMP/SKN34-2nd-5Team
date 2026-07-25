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
from core.formatters import percent, signed_phrase, signed_tone
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


st.session_state.setdefault("reviewer_detail_view", "활동 변화")


def _open_post_validation() -> None:
    """Open the post-validation view when its disclosure control is enabled."""
    if st.session_state.get("validation_mode"):
        st.session_state["reviewer_detail_view"] = "사후 검증"


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
        on_change=_open_post_validation,
    )

profile_header(
    user_id=str(row["user_id"]),
    rank=int(row["priority_rank"]),
    model_judgment=str(row["model_judgment"]),
    retained_score=float(row["retained_score"]),
    weakened_score=float(row["weakened_score"]),
    stopped_score=float(row["stopped_score"]),
    selected_for_review=bool(row["crm_target"]),
    selection_year=int(row["selection_year"]),
    target_year=int(row["target_year"]),
)

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
                "delta": signed_phrase(
                    row["review_count_decline_rate"], percent,
                    when_positive="감소", when_negative="증가",
                ),
                "delta_tone": signed_tone(row["review_count_decline_rate"]),
                "before_value": float(row["baseline_review_count"]),
                "after_value": float(row["recent_review_count"]),
                "icon": "rate_review",
            },
            {
                "label": "활동 월",
                "before": f"{int(row['baseline_active_months'])}개월",
                "after": f"{int(row['recent_active_months'])}개월",
                "delta": signed_phrase(
                    row["active_month_decline_rate"], percent,
                    when_positive="감소", when_negative="증가",
                ),
                "delta_tone": signed_tone(row["active_month_decline_rate"]),
                "before_value": float(row["baseline_active_months"]),
                "after_value": float(row["recent_active_months"]),
                "icon": "calendar_month",
            },
            {
                "label": "고유 음식점",
                "before": f"{int(row['baseline_unique_business_count'])}곳",
                "after": f"{int(row['recent_unique_business_count'])}곳",
                "delta": signed_phrase(
                    row["unique_business_decline_rate"], percent,
                    when_positive="감소", when_negative="증가",
                ),
                "delta_tone": signed_tone(row["unique_business_decline_rate"]),
                "before_value": float(row["baseline_unique_business_count"]),
                "after_value": float(row["recent_unique_business_count"]),
                "icon": "location_on",
            },
            {
                "label": "리뷰 공백",
                "before": f"{float(row['baseline_recency_days']):.0f}일",
                "after": f"{float(row['recent_recency_days']):.0f}일",
                "delta": f"{float(row['recency_increase_days']):+.0f}일",
                "delta_tone": (
                    "positive"
                    if float(row["recency_increase_days"]) < 0
                    else "warning"
                ),
                "before_value": float(row["baseline_recency_days"]),
                "after_value": float(row["recent_recency_days"]),
                "icon": "hourglass_empty",
            },
        ]
    )

    evidence_column, activity_column, interval_column = st.columns(
        [0.9, 1, 1],
        gap="medium",
    )
    with evidence_column:
        section_header(
            "왜 우선 검토 대상인가",
            "관찰 가능한 근거를 강한 순서로 정리했습니다.",
            "규칙 기반 프로토타입",
        )
        evidence_list(
            [(signal.name, signal.evidence, signal.group) for signal in signals[:3]]
        )
    with activity_column:
        section_header("활동 변화 요약", "과거와 최근")
        st.plotly_chart(
            profile_activity(row),
            width="stretch",
            key="reviewer_activity_chart",
            config={"displayModeBar": False, "responsive": True},
        )
    with interval_column:
        section_header("작성 주기 변화", "리뷰 간격과 공백")
        st.plotly_chart(
            interval_comparison(row),
            width="stretch",
            key="reviewer_interval_chart",
            config={"displayModeBar": False, "responsive": True},
        )

    detail_view = st.segmented_control(
        "상세 보기",
        ["활동 변화", "월별 타임라인", "사후 검증"],
        key="reviewer_detail_view",
        width="stretch",
    )

    if detail_view == "월별 타임라인":
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
                config={"displayModeBar": False, "responsive": True},
            )
    elif detail_view == "사후 검증" and validation_mode:
        st.info(
            "사후 검증 결과입니다. 운영 당시에는 알 수 없었던 정보이므로 "
            "예측 근거와 분리해 표시합니다.",
            icon=":material/visibility:",
        )
        truth_cols = st.columns(3, gap="large")
        with truth_cols[0]:
            st.metric("실제 상태", str(row.get("retention_state_label", "—")))
        with truth_cols[1]:
            st.metric("타깃 연도 리뷰", f"{int(row.get('target_review_count', 0)):,}건")
        with truth_cols[2]:
            st.metric("타깃 연도 활동 월", f"{int(row.get('target_active_months', 0))}개월")
    elif detail_view == "사후 검증":
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
            ("핵심 신호", str(row["core_signal"])),
            ("전략 후보", strategy["secondary"]),
            ("향후 채널", strategy["channel"]),
        ],
    )

    section_header(
        "관리자 판단",
        "모델 판단과 활동 근거를 확인한 뒤 현재 세션에서만 분류합니다.",
        "규칙 기반 프로토타입",
    )
    decisions = st.session_state.setdefault("reviewer_decisions", {})
    decision_options = ["복귀 관리", "활동 회복", "관찰 유지", "대상 제외"]
    recommendation_map = {
        0: "관찰 유지",
        1: "활동 회복",
        2: "복귀 관리",
    }
    default_decision = decisions.get(
        str(row["user_id"]),
        recommendation_map.get(int(row["predicted_state"]), "관찰 유지"),
    )
    with st.form("reviewer_decision_form", border=False):
        manager_decision = st.radio(
            "검토 결과",
            decision_options,
            index=decision_options.index(default_decision),
            help="이 선택은 브라우저 세션에만 유지되며 CRM이나 데이터베이스에 저장되지 않습니다.",
        )
        submitted = st.form_submit_button(
            "세션 판단 적용",
            icon=":material/check_circle:",
            width="stretch",
        )
    if submitted:
        decisions[str(row["user_id"])] = manager_decision
        st.toast(
            f"{manager_decision}으로 임시 분류했습니다.",
            icon=":material/check_circle:",
        )
    st.html(
        """
        <div class="rr-decision-note">
          영구 저장·담당자 배정·캠페인 실행은 지원하지 않습니다.
          현재 선택은 운영 흐름을 검증하기 위한 세션 임시 판단입니다.
        </div>
        """
    )
    if st.button(
        "플레이북에서 전략 확인",
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

render_warnings(data.warnings)
footer(data.data_mode)
