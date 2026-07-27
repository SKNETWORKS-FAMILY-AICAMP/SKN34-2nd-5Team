from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st

from core.components import (
    footer,
    page_intro,
    render_warnings,
    reviewer_list,
    stat_card_row,
)
from core.data import load_app_data, operational_profile_export
from core.decisions import UNDECIDED_LABEL, with_manager_decisions
from core.insights import risk_signals


query_reviewer = st.query_params.get("reviewer")
returning_to_queue = st.session_state.pop("_returning_to_reviewer_queue", False)
if query_reviewer and not returning_to_queue:
    st.session_state["selected_reviewer_id"] = str(query_reviewer)
    st.session_state["reviewer_workspace_mode"] = "detail"

if st.session_state.get("reviewer_workspace_mode") == "detail":
    runpy.run_path(
        str(Path(__file__).with_name("reviewer_360.py")),
        run_name="__reviewer_360__",
    )
    st.stop()

data = load_app_data()
profiles = with_manager_decisions(data.reviewer_profiles)

page_intro(
    f"Reviewer worklist · {data.model_version}",
    "통합 리뷰어 검토 워크리스트",
    "약화·중단 점수를 하나의 순위로 검토하고 Reviewer 360에서 활동 근거를 확인합니다.",
    ["현재 데모에서 사용 가능" if data.data_mode == "demo" else "현재 사용 가능"],
)

all_ids = set(profiles["user_id"].astype(str))
done_count = int(profiles["manager_decision"].ne(UNDECIDED_LABEL).sum())
pending_count = len(all_ids) - done_count

status_filter = st.segmented_control(
    "검토 상태",
    options=["전체", "미검토", "검토 완료"],
    default="전체",
    key="worklist_status_filter",
    label_visibility="collapsed",
)
risk_type_options = ["전체"] + profiles["risk_type"].value_counts().index.tolist()
risk_type_filter = st.segmented_control(
    "위험 유형",
    options=risk_type_options,
    default="전체",
    key="worklist_risk_type_filter",
    label_visibility="collapsed",
)
stat_card_row(
    [
        ("전체", f"{len(all_ids):,}명", None),
        ("미검토", f"{pending_count:,}명", None),
        ("검토 완료", f"{done_count:,}명", "good" if done_count else None),
    ]
)

with st.container(horizontal=True, vertical_alignment="bottom"):
    search_text = st.text_input(
        "리뷰어 ID 검색",
        placeholder="reviewer ID",
        icon=":material/search:",
        key="queue_search",
        persist_state="session",
        width="stretch",
    )
    with st.popover("필터와 정렬", icon=":material/tune:", width="stretch"):
        selected_states = st.multiselect(
            "모델 판단",
            options=["유지 우세", "약화 우세", "중단 우세"],
            default=["약화 우세", "중단 우세"],
            key="queue_states",
            persist_state="session",
        )
        selected_signals = st.multiselect(
            "핵심 행동 신호",
            options=sorted(profiles["risk_type"].dropna().unique().tolist()),
            placeholder="전체",
            key="queue_signals",
            persist_state="session",
        )
        crm_filter = st.selectbox(
            "통합 검토 범위",
            ["통합 상위 20%", "전체", "상위 20% 제외"],
            key="queue_crm",
            persist_state="session",
        )
        sort_rule = st.selectbox(
            "정렬",
            [
                "통합 우선순위",
                "중단 점수 높은 순",
                "약화 점수 높은 순",
                "활동 감소순",
                "리뷰 공백순",
            ],
            key="queue_sort",
            persist_state="session",
        )
    st.download_button(
        "CSV 다운로드",
        data=operational_profile_export(
            profiles,
            list(data.model_metadata.get("feature_columns", [])),
        ).to_csv(index=False).encode("utf-8-sig"),
        file_name="reviewer_risk_worklist.csv",
        mime="text/csv",
        icon=":material/download:",
    )

filtered = profiles.copy()
if search_text:
    filtered = filtered[
        filtered["user_id"].astype(str).str.contains(
            search_text.strip(),
            case=False,
            regex=False,
        )
    ]
if selected_states:
    filtered = filtered[filtered["model_judgment"].isin(selected_states)]
if selected_signals:
    filtered = filtered[filtered["risk_type"].isin(selected_signals)]
if risk_type_filter and risk_type_filter != "전체":
    filtered = filtered[filtered["risk_type"].eq(risk_type_filter)]
if crm_filter == "통합 상위 20%":
    filtered = filtered[filtered["crm_target"].eq(1)]
elif crm_filter == "상위 20% 제외":
    filtered = filtered[filtered["crm_target"].eq(0)]
if status_filter == "미검토":
    filtered = filtered[filtered["manager_decision"].eq(UNDECIDED_LABEL)]
elif status_filter == "검토 완료":
    filtered = filtered[filtered["manager_decision"].ne(UNDECIDED_LABEL)]

sort_map = {
    "통합 우선순위": ("priority_rank", True),
    "중단 점수 높은 순": ("stopped_score", False),
    "약화 점수 높은 순": ("weakened_score", False),
    "활동 감소순": ("active_month_decline_rate", False),
    "리뷰 공백순": ("recent_recency_days", False),
}
sort_column, ascending = sort_map[sort_rule]
filtered = filtered.sort_values(sort_column, ascending=ascending)
st.session_state["worklist_ordered_ids"] = filtered["user_id"].astype(str).tolist()

if filtered.empty:
    st.warning("현재 조건에 해당하는 리뷰어가 없습니다.", icon=":material/search_off:")
    render_warnings(data.warnings)
    footer(data.data_mode)
    st.stop()

visible_count = st.session_state.setdefault("worklist_visible_count", 50)
visible = filtered.head(visible_count)

rows = []
for _, row in visible.iterrows():
    top_metrics = [signal.evidence for signal in risk_signals(row)[:2]]
    user_id = str(row["user_id"])
    completed_label = (
        None
        if row["manager_decision"] == UNDECIDED_LABEL
        else str(row["manager_decision"])
    )
    rows.append(
        {
            "user_id": user_id,
            "rank_label": f"{int(row['priority_rank'])}위",
            "model_judgment": str(row["model_judgment"]),
            "metrics": top_metrics,
            "signal_label": str(row["core_signal"]),
            "action": str(row["recommended_review"]),
            "completed_label": completed_label,
        }
    )
reviewer_list(rows)

remaining = len(filtered) - len(visible)
footer_cols = st.columns([1, 1, 1])
with footer_cols[1]:
    st.html(
        f"<p style='text-align:center;font-size:.78rem;color:var(--rr-muted)'>"
        f"{len(filtered):,}명 중 {len(visible):,}명 표시</p>"
    )
    if remaining > 0:
        if st.button(
            f"더 보기 · {min(50, remaining)}명 추가",
            key="worklist_load_more",
            width="stretch",
        ):
            st.session_state["worklist_visible_count"] = visible_count + 50
            st.rerun()

render_warnings(data.warnings)
footer(data.data_mode)
