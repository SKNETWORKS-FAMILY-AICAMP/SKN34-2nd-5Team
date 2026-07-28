from __future__ import annotations

import html

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
from core.decisions import (
    UNDECIDED_LABEL,
    apply_decision,
    cancel_decision,
    get_decision,
)
from core.formatters import percent, signed_phrase, signed_tone
from core.insights import DECISION_STATE_MAP, risk_signals, strategy_for


data = load_app_data()
profiles = data.reviewer_profiles

selected_user = st.session_state.get("selected_reviewer_id")
if selected_user not in set(profiles["user_id"].astype(str)):
    selected_user = str(profiles.iloc[0]["user_id"])
    st.session_state["selected_reviewer_id"] = selected_user

row = profiles.loc[profiles["user_id"].astype(str).eq(selected_user)].iloc[0]
strategy = strategy_for(row)
signals = risk_signals(row)
prior_available = bool(row["prior_activity_available"])
comparison_unavailable = "전년도 대비 변화율 계산 불가"
comparison_empty = f"{int(row['comparison_year'])}년 비교 활동 없음"

ordered_ids = st.session_state.get("worklist_ordered_ids") or (
    profiles.sort_values("priority_rank")["user_id"].astype(str).tolist()
)
try:
    current_index = ordered_ids.index(selected_user)
except ValueError:
    current_index = None


def _go_to_reviewer(user_id: str) -> None:
    st.session_state["selected_reviewer_id"] = user_id
    st.query_params["reviewer"] = user_id
    st.rerun()


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

with st.container(
    key="rr_nav_bar",
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="center",
):
    if st.button(
        "이전 리뷰어",
        icon=":material/chevron_left:",
        key="prev_reviewer",
        disabled=current_index is None or current_index == 0,
    ):
        _go_to_reviewer(ordered_ids[current_index - 1])
    if current_index is not None:
        st.caption(f"워크리스트 순서 기준 · {current_index + 1:,} / {len(ordered_ids):,}")
    else:
        st.caption("전체 순위 기준")
    if st.button(
        "다음 리뷰어",
        icon=":material/chevron_right:",
        key="next_reviewer",
        disabled=current_index is None or current_index >= len(ordered_ids) - 1,
    ):
        _go_to_reviewer(ordered_ids[current_index + 1])

profile_header(
    user_id=str(row["user_id"]),
    rank=int(row["priority_rank"]),
    total_reviewers=len(profiles),
    model_judgment=str(row["model_judgment"]),
    retained_score=float(row["retained_score"]),
    weakened_score=float(row["weakened_score"]),
    stopped_score=float(row["stopped_score"]),
    selected_for_review=bool(row["crm_target"]),
    comparison_year=int(row["comparison_year"]),
    selection_year=int(row["selection_year"]),
    target_year=int(row["target_year"]),
)

main_column, action_column = st.columns([1.72, 0.58], gap="large")
with main_column:
    section_header(
        "활동이 이렇게 변했습니다",
        (
            f"{int(row['comparison_year'])}년 비교 활동과 "
            f"{int(row['selection_year'])}년 선정·피처 마감 활동을 비교했습니다."
        ),
        "현재 사용 가능",
    )
    change_story(
        [
            {
                "label": "리뷰 수",
                "before": (
                    f"{int(row['baseline_review_count'])}건"
                    if prior_available
                    else comparison_empty
                ),
                "after": f"{int(row['recent_review_count'])}건",
                "delta": (
                    signed_phrase(
                        row["review_count_decline_rate"],
                        percent,
                        when_positive="감소",
                        when_negative="증가",
                    )
                    if prior_available
                    else comparison_unavailable
                ),
                "delta_tone": (
                    signed_tone(row["review_count_decline_rate"])
                    if prior_available
                    else "muted"
                ),
                "icon": "rate_review",
            },
            {
                "label": "활동 월",
                "before": (
                    f"{int(row['baseline_active_months'])}개월"
                    if prior_available
                    else comparison_empty
                ),
                "after": f"{int(row['recent_active_months'])}개월",
                "delta": (
                    signed_phrase(
                        row["active_month_decline_rate"],
                        percent,
                        when_positive="감소",
                        when_negative="증가",
                    )
                    if prior_available
                    else comparison_unavailable
                ),
                "delta_tone": (
                    signed_tone(row["active_month_decline_rate"])
                    if prior_available
                    else "muted"
                ),
                "icon": "calendar_month",
            },
            {
                "label": "고유 음식점",
                "before": (
                    f"{int(row['baseline_unique_business_count'])}곳"
                    if prior_available
                    else comparison_empty
                ),
                "after": f"{int(row['recent_unique_business_count'])}곳",
                "delta": (
                    signed_phrase(
                        row["unique_business_decline_rate"],
                        percent,
                        when_positive="감소",
                        when_negative="증가",
                    )
                    if prior_available
                    else comparison_unavailable
                ),
                "delta_tone": (
                    signed_tone(row["unique_business_decline_rate"])
                    if prior_available
                    else "muted"
                ),
                "icon": "location_on",
            },
            {
                "label": "리뷰 공백",
                "before": (
                    f"{float(row['baseline_recency_days']):.0f}일"
                    if prior_available
                    else comparison_empty
                ),
                "after": f"{float(row['recent_recency_days']):.0f}일",
                "delta": (
                    f"{float(row['recency_increase_days']):+.0f}일"
                    if prior_available
                    else comparison_unavailable
                ),
                "delta_tone": (
                    (
                        "positive"
                        if float(row["recency_increase_days"]) < 0
                        else "warning"
                    )
                    if prior_available
                    else "muted"
                ),
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
        with st.container(key="rr_chart_activity"):
            section_header("활동 변화 요약", "과거와 최근")
            st.plotly_chart(
                profile_activity(row),
                width="stretch",
                key="reviewer_activity_chart",
                config={"displayModeBar": False, "responsive": True},
            )
    with interval_column:
        with st.container(key="rr_chart_interval"):
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
            st.metric(
                f"{int(row['target_year'])}년 리뷰",
                f"{int(row.get('target_review_count', 0)):,}건",
            )
        with truth_cols[2]:
            st.metric(
                f"{int(row['target_year'])}년 활동 월",
                f"{int(row.get('target_active_months', 0))}개월",
            )
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

    user_id_str = str(row["user_id"])
    sample_id_str = str(row["sample_id"])
    model_version = str(row["model_version"])
    decision_options = ["리뷰 다시 시작 유도", "리뷰 활동 늘리기", "변화 지켜보기", "이번엔 제외"]
    existing_decision = get_decision(model_version, sample_id_str)
    if existing_decision not in decision_options:
        existing_decision = None
    recommended_decision = DECISION_STATE_MAP.get(
        int(row["predicted_state"]), "변화 지켜보기"
    )
    with st.container(key="rr_decision_panel"):
        section_header(
            "관리자 판단",
            "모델 판단과 활동 근거를 확인한 뒤 분류합니다.",
            "규칙 기반 프로토타입",
        )
        if existing_decision:
            with st.container(horizontal=True, vertical_alignment="center"):
                st.html(
                    f'<span class="rr-pill rr-pill--decided">판단 완료 · {html.escape(existing_decision)}</span>'
                )
                if st.button(
                    "취소", key="cancel_decision", icon=":material/close:"
                ):
                    cancel_decision(model_version, sample_id_str)
                    st.toast("판단을 취소했습니다.", icon=":material/backspace:")
                    st.rerun()
        else:
            st.html(
                f'<span class="rr-pill">아직 판단 전 · 모델 추천 {html.escape(recommended_decision)}</span>'
            )
        with st.container(key="rr_decision_radio"):
            with st.form("reviewer_decision_form", border=False):
                manager_decision = st.radio(
                    "검토 결과",
                    decision_options,
                    index=(
                        decision_options.index(existing_decision)
                        if existing_decision
                        else None
                    ),
                    label_visibility="collapsed",
                    help="이 선택은 이 앱의 로컬 저장소에 보관되며 CRM이나 외부 데이터베이스에는 연동되지 않습니다.",
                )
                submitted = st.form_submit_button(
                    "세션 판단 적용",
                    icon=":material/check_circle:",
                    type="primary",
                    width="stretch",
                )
        if submitted:
            if manager_decision is None:
                st.toast("검토 결과를 먼저 선택하세요.", icon=":material/error:")
            else:
                apply_decision(model_version, sample_id_str, manager_decision)
                st.toast(
                    f"{manager_decision}으로 분류했습니다.",
                    icon=":material/check_circle:",
                )
                st.rerun()
        if current_index is not None and current_index < len(ordered_ids) - 1:
            if st.button(
                "다음 리뷰어로",
                key="decision_next_reviewer",
                icon=":material/arrow_forward:",
                width="stretch",
            ):
                _go_to_reviewer(ordered_ids[current_index + 1])
        st.html(
            """
            <div class="rr-decision-note">
              이 판단은 이 서버의 로컬 파일에 저장되어 새로고침·재시작 후에도
              유지되지만, 여러 세션이 같은 저장소를 공유합니다. 담당자 배정·
              CRM 연동·감사 이력은 지원하지 않습니다.
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
        st.session_state["playbook_context"] = {
            "sample_id": sample_id_str,
            "user_id": user_id_str,
            "manager_decision": existing_decision or UNDECIDED_LABEL,
            "risk_type": str(row["risk_type"]),
            "model_judgment": str(row["model_judgment"]),
            "priority_rank": int(row["priority_rank"]),
            "priority_top_percent": float(row["priority_top_percent"]),
            "priority_score": float(row["priority_score"]),
            "selected_for_crm": bool(row["crm_target"]),
        }
        st.session_state["playbook_view_mode"] = "현재 리뷰어에게 추천"
        st.switch_page("views/playbook.py")
    future_integration(
        "CRM 캠페인 배정",
        "개입 일자, 담당자, 채널, 참여 및 복귀 결과",
    )

render_warnings(data.warnings)
footer(data.data_mode)
