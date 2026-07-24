from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st

from core.components import footer, page_intro, render_warnings, section_header
from core.data import load_app_data


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
profiles = data.reviewer_profiles.copy()

page_intro(
    "Reviewer worklist",
    "검토 대상을 찾고 비교합니다",
    "검색과 필터 결과를 내려받거나, 행을 선택해 Reviewer 360에서 변화 근거와 권장 행동을 확인합니다.",
    ["현재 데모에서 사용 가능" if data.data_mode == "demo" else "현재 사용 가능"],
)
render_warnings(data.warnings)

with st.container(horizontal=True, vertical_alignment="bottom"):
    search_text = st.text_input(
        "리뷰어 ID 검색",
        placeholder="reviewer ID",
        icon=":material/search:",
        key="queue_search",
        persist_state="session",
        width="stretch",
    )
    selected_tiers = st.multiselect(
        "위험 등급",
        options=["긴급 관리", "집중 관리", "관찰 대상", "일반"],
        default=["긴급 관리", "집중 관리"],
        key="queue_tiers",
        persist_state="session",
        width=220,
    )
    selected_types = st.multiselect(
        "위험 유형",
        options=sorted(profiles["risk_type"].dropna().unique().tolist()),
        placeholder="전체",
        key="queue_types",
        persist_state="session",
        width=230,
    )
    crm_filter = st.selectbox(
        "CRM 대상",
        ["Top 20% 대상", "전체", "대상 제외"],
        key="queue_crm",
        persist_state="session",
        width=150,
    )
    sort_rule = st.selectbox(
        "정렬",
        ["위험 순위순", "점수 높은 순", "활동 감소순", "리뷰 공백순"],
        key="queue_sort",
        persist_state="session",
        width=160,
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
if selected_tiers:
    filtered = filtered[filtered["risk_tier"].isin(selected_tiers)]
if selected_types:
    filtered = filtered[filtered["risk_type"].isin(selected_types)]
if crm_filter == "Top 20% 대상":
    filtered = filtered[filtered["crm_target"].eq(1)]
elif crm_filter == "대상 제외":
    filtered = filtered[filtered["crm_target"].eq(0)]

sort_map = {
    "위험 순위순": ("risk_rank", True),
    "점수 높은 순": ("risk_score", False),
    "활동 감소순": ("active_month_decline_rate", False),
    "리뷰 공백순": ("recent_recency_days", False),
}
sort_column, ascending = sort_map[sort_rule]
filtered = filtered.sort_values(sort_column, ascending=ascending)

summary = st.columns(4, gap="large")
with summary[0]:
    st.metric("검색 결과", f"{len(filtered):,}명")
with summary[1]:
    st.metric("긴급 검토", f"{int(filtered['risk_tier'].eq('긴급 관리').sum()):,}명")
with summary[2]:
    st.metric("CRM 대상", f"{int(filtered['crm_target'].eq(1).sum()):,}명")
with summary[3]:
    mean_score = float(filtered["risk_score"].mean()) if not filtered.empty else 0.0
    st.metric("평균 위험 점수", f"{mean_score:.3f}")

section_header(
    "리뷰어 워크리스트",
    "행을 선택하면 비교하거나 Reviewer 360으로 이동할 수 있습니다.",
)

if filtered.empty:
    st.warning("현재 조건에 해당하는 리뷰어가 없습니다.", icon=":material/search_off:")
    footer(data.data_mode)
    st.stop()

table = filtered.head(500).copy()
table["리뷰어"] = table["user_id"]
table["등급"] = table["risk_tier"]
table["모델 점수"] = table["risk_score"]
table["위험 유형"] = table["risk_type"]
table["리뷰 수"] = (
    table["baseline_review_count"].round().astype(int).astype(str)
    + " → "
    + table["recent_review_count"].round().astype(int).astype(str)
)
table["활동 월"] = (
    table["baseline_active_months"].round().astype(int).astype(str)
    + " → "
    + table["recent_active_months"].round().astype(int).astype(str)
)
table["고유 음식점"] = (
    table["baseline_unique_business_count"].round().astype(int).astype(str)
    + " → "
    + table["recent_unique_business_count"].round().astype(int).astype(str)
)
table["리뷰 공백"] = table["recent_recency_days"].round().astype(int).astype(str) + "일"
table["권장 행동"] = table["recommended_action"]
display = table[
    [
        "risk_rank",
        "리뷰어",
        "등급",
        "모델 점수",
        "위험 유형",
        "리뷰 수",
        "활동 월",
        "고유 음식점",
        "리뷰 공백",
        "권장 행동",
    ]
].rename(columns={"risk_rank": "순위"})

selection = st.dataframe(
    display,
    hide_index=True,
    width="stretch",
    height=540,
    key="reviewer_worklist",
    on_select="rerun",
    selection_mode="multi-row",
    column_config={
        "순위": st.column_config.NumberColumn(format="%d위", width="small"),
        "리뷰어": st.column_config.TextColumn(width="medium"),
        "모델 점수": st.column_config.ProgressColumn(
            min_value=0.0,
            max_value=1.0,
            format="%.4f",
            width="medium",
        ),
        "권장 행동": st.column_config.TextColumn(width="large"),
    },
)

selected_rows = list(selection.selection.rows)
selected_profiles = table.iloc[selected_rows] if selected_rows else table.iloc[0:0]

with st.container(horizontal=True, horizontal_alignment="right"):
    csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "현재 결과 CSV",
        data=csv_data,
        file_name="reviewer_risk_worklist.csv",
        mime="text/csv",
        icon=":material/download:",
    )
    open_disabled = len(selected_profiles) != 1
    if st.button(
        "Reviewer 360 열기",
        type="primary",
        icon=":material/person_search:",
        disabled=open_disabled,
        key="open_reviewer",
    ):
        st.session_state["selected_reviewer_id"] = str(
            selected_profiles.iloc[0]["user_id"]
        )
        st.session_state["reviewer_workspace_mode"] = "detail"
        st.rerun()

if len(selected_profiles) >= 2:
    section_header(
        "선택 리뷰어 비교",
        "최대 4명의 핵심 행동 변화를 같은 기준으로 비교합니다.",
    )
    comparison = selected_profiles.head(4).copy()
    comparison_view = comparison[
        [
            "user_id",
            "risk_score",
            "review_count_decline_rate",
            "active_month_decline_rate",
            "unique_business_decline_rate",
            "recency_increase_days",
        ]
    ].rename(
        columns={
            "user_id": "리뷰어",
            "risk_score": "모델 점수",
            "review_count_decline_rate": "리뷰 감소율",
            "active_month_decline_rate": "활동 월 감소율",
            "unique_business_decline_rate": "탐색 감소율",
            "recency_increase_days": "공백 증가일",
        }
    )
    st.dataframe(
        comparison_view,
        hide_index=True,
        width="stretch",
        column_config={
            "모델 점수": st.column_config.NumberColumn(format="%.4f"),
            "리뷰 감소율": st.column_config.NumberColumn(format="%.1%%"),
            "활동 월 감소율": st.column_config.NumberColumn(format="%.1%%"),
            "탐색 감소율": st.column_config.NumberColumn(format="%.1%%"),
            "공백 증가일": st.column_config.NumberColumn(format="%.0f일"),
        },
    )

st.caption("표에는 성능과 가독성을 위해 현재 필터 결과 중 상위 500명까지 표시합니다.")
footer(data.data_mode)
