from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st

from core.components import (
    footer,
    page_intro,
    render_warnings,
    section_header,
)
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
    "Reviewer worklist · v03",
    "통합 리뷰어 검토 워크리스트",
    "약화·중단 점수를 하나의 순위로 검토하고 Reviewer 360에서 활동 근거를 확인합니다.",
    ["현재 데모에서 사용 가능" if data.data_mode == "demo" else "현재 사용 가능"],
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
            options=sorted(profiles["core_signal"].dropna().unique().tolist()),
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
    filtered = filtered[filtered["core_signal"].isin(selected_signals)]
if crm_filter == "통합 상위 20%":
    filtered = filtered[filtered["crm_target"].eq(1)]
elif crm_filter == "상위 20% 제외":
    filtered = filtered[filtered["crm_target"].eq(0)]

sort_map = {
    "통합 우선순위": ("priority_rank", True),
    "중단 점수 높은 순": ("stopped_score", False),
    "약화 점수 높은 순": ("weakened_score", False),
    "활동 감소순": ("active_month_decline_rate", False),
    "리뷰 공백순": ("recent_recency_days", False),
}
sort_column, ascending = sort_map[sort_rule]
filtered = filtered.sort_values(sort_column, ascending=ascending)

st.caption(
    f"검색 결과 {len(filtered):,}명 · "
    f"통합 상위 20% {int(filtered['crm_target'].eq(1).sum()):,}명 · "
    "클래스 점수는 확률이 아닌 상대 모델 점수입니다."
)

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
table["모델 판단"] = table["model_judgment"]
table["유지 점수"] = table["retained_score"]
table["약화 점수"] = table["weakened_score"]
table["중단 점수"] = table["stopped_score"]
table["핵심 신호"] = table["core_signal"]
table["리뷰 수 변화"] = table.apply(
    lambda row: [row["baseline_review_count"], row["recent_review_count"]],
    axis=1,
)
table["활동 월 변화"] = table.apply(
    lambda row: [row["baseline_active_months"], row["recent_active_months"]],
    axis=1,
)
table["탐색 변화"] = table.apply(
    lambda row: [
        row["baseline_unique_business_count"],
        row["recent_unique_business_count"],
    ],
    axis=1,
)
table["리뷰 공백"] = table["recent_recency_days"].round().astype(int).astype(str) + "일"
table["권장 검토"] = table["recommended_review"]
display = table[
    [
        "priority_rank",
        "리뷰어",
        "모델 판단",
        "유지 점수",
        "약화 점수",
        "중단 점수",
        "핵심 신호",
        "리뷰 수 변화",
        "활동 월 변화",
        "탐색 변화",
        "리뷰 공백",
        "권장 검토",
    ]
].rename(columns={"priority_rank": "통합 순위"})

selection = st.dataframe(
    display,
    hide_index=True,
    width="stretch",
    height=540,
    key="reviewer_worklist",
    on_select="rerun",
    selection_mode="multi-row",
    column_config={
        "통합 순위": st.column_config.NumberColumn(
            format="%d위", width="small", pinned=True
        ),
        "리뷰어": st.column_config.TextColumn(width="medium", pinned=True),
        "유지 점수": st.column_config.ProgressColumn(
            min_value=0.0,
            max_value=1.0,
            format="%.3f",
            width="small",
        ),
        "약화 점수": st.column_config.ProgressColumn(
            min_value=0.0,
            max_value=1.0,
            format="%.3f",
            width="small",
        ),
        "중단 점수": st.column_config.ProgressColumn(
            min_value=0.0,
            max_value=1.0,
            format="%.3f",
            width="small",
        ),
        "리뷰 수 변화": st.column_config.LineChartColumn(
            "리뷰 수 · 과거→최근", width="medium"
        ),
        "활동 월 변화": st.column_config.LineChartColumn(
            "활동 월 · 과거→최근", width="medium"
        ),
        "탐색 변화": st.column_config.LineChartColumn(
            "음식점 · 과거→최근", width="medium"
        ),
        "권장 검토": st.column_config.TextColumn(width="large"),
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
            "model_judgment",
            "retained_score",
            "weakened_score",
            "stopped_score",
            "review_count_decline_rate",
            "active_month_decline_rate",
            "unique_business_decline_rate",
            "recency_increase_days",
        ]
    ].rename(
        columns={
            "user_id": "리뷰어",
            "model_judgment": "모델 판단",
            "retained_score": "유지 점수",
            "weakened_score": "약화 점수",
            "stopped_score": "중단 점수",
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
            "유지 점수": st.column_config.NumberColumn(format="%.3f"),
            "약화 점수": st.column_config.NumberColumn(format="%.3f"),
            "중단 점수": st.column_config.NumberColumn(format="%.3f"),
            "리뷰 감소율": st.column_config.NumberColumn(format="percent"),
            "활동 월 감소율": st.column_config.NumberColumn(format="percent"),
            "탐색 감소율": st.column_config.NumberColumn(format="percent"),
            "공백 증가일": st.column_config.NumberColumn(format="%.0f일"),
        },
    )

st.caption("표에는 성능과 가독성을 위해 현재 필터 결과 중 상위 500명까지 표시합니다.")
render_warnings(data.warnings)
footer(data.data_mode)
