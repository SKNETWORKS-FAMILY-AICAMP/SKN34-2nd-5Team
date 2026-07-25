from __future__ import annotations

import pandas as pd
import streamlit as st

from core.charts import retention_state_distribution
from core.components import (
    footer,
    metric_strip,
    operations_flow,
    page_intro,
    priority_queue,
    render_warnings,
    section_header,
    signal_bars,
    validated_policy_brief,
)
from core.data import load_app_data


data = load_app_data()
profiles = data.reviewer_profiles.copy()
policy = data.primary_policy.iloc[0] if not data.primary_policy.empty else pd.Series()

total_reviewers = len(profiles)
target_users = int(policy.get("target_users", profiles["crm_target"].sum()))
captured_users = int(policy.get("status_loss_captured", 0))
precision = float(policy.get("status_loss_precision", 0.0))
recall = float(policy.get("status_loss_recall", 0.0))
lift = float(policy.get("status_loss_lift", 0.0))
stopped_captured = int(policy.get("stopped_captured", 0))
stopped_recall = float(policy.get("stopped_recall", 0.0))
weakened_captured = int(policy.get("weakened_captured", 0))
weakened_recall = float(policy.get("weakened_recall", 0.0))
predicted_counts = profiles["predicted_state"].value_counts()

page_intro(
    "Operations briefing · v03 · Test 2019",
    "오늘의 리텐션 운영",
    "약화·중단 점수를 통합한 우선순위로 검토 대상을 확인하고 운영자가 개입 방향을 판단합니다.",
    ["현재 데모에서 사용 가능" if data.data_mode == "demo" else "현재 사용 가능"],
)

metric_strip(
    [
        ("Test 검증 대상", f"{total_reviewers:,}명", "선정 2017 · 타깃 2019"),
        ("통합 검토 대상", f"{target_users:,}명", "통합 우선순위 상위 20%"),
        ("모델 판단 · 약화 우세", f"{int(predicted_counts.get(1, 0)):,}명", "전체 검증 대상"),
        ("모델 판단 · 중단 우세", f"{int(predicted_counts.get(2, 0)):,}명", "전체 검증 대상"),
    ]
)

queue_column, brief_column = st.columns([1.68, 0.62], gap="large")
with queue_column:
    section_header(
        "통합 우선 검토 큐",
        "약화·중단 상대 점수를 합산한 순서입니다. 행을 선택하면 Reviewer 360으로 이동합니다.",
        "현재 사용 가능",
    )
    queue = profiles.loc[profiles["crm_target"].eq(1)].nsmallest(6, "priority_rank")
    priority_queue(
        [
            {
                "rank": f"{int(row.priority_rank):02d}",
                "user_id": str(row.user_id),
                "model_judgment": str(row.model_judgment),
                "retained_score": float(row.retained_score),
                "weakened_score": float(row.weakened_score),
                "stopped_score": float(row.stopped_score),
                "core_signal": str(row.core_signal),
                "action": str(row.recommended_review),
            }
            for row in queue.itertuples()
        ]
    )
    if st.button(
        "리뷰어 관리에서 전체 대상 보기",
        type="primary",
        icon=":material/arrow_forward:",
        key="primary_action",
    ):
        st.session_state["reviewer_workspace_mode"] = "list"
        st.switch_page("views/risk_queue.py")

with brief_column:
    section_header(
        "검증된 운영 정책",
        "사후 Test 정답으로 평가한 통합 큐 성과입니다.",
    )
    validated_policy_brief(
        target_users=target_users,
        captured_users=captured_users,
        precision=precision,
        recall=recall,
        lift=lift,
        stopped_captured=stopped_captured,
        stopped_recall=stopped_recall,
        weakened_captured=weakened_captured,
        weakened_recall=weakened_recall,
    )

signal_counts = sorted(
    [
    (
        "활동 월 50% 이상 감소",
        int(profiles["active_month_decline_rate"].ge(0.5).sum()),
    ),
    (
        "리뷰 수 50% 이상 감소",
        int(profiles["review_count_decline_rate"].ge(0.5).sum()),
    ),
    (
        "음식점 탐색 50% 이상 감소",
        int(profiles["unique_business_decline_rate"].ge(0.5).sum()),
    ),
    (
        "마지막 리뷰 공백 30일 이상 증가",
        int(profiles["recency_increase_days"].ge(30).sum()),
    ),
    ],
    key=lambda item: item[1],
    reverse=True,
)

signal_column, state_column, flow_column = st.columns([1.05, 0.9, 1], gap="large")
with signal_column:
    section_header(
        "어떤 신호가 늘고 있나",
        "프로필 데이터에서 직접 집계한 행동 변화입니다.",
        "현재 사용 가능",
    )
    signal_bars(signal_counts)

with state_column:
    section_header(
        "모델 판단 분포",
        "임계값 정책에 따른 전체 분포이며 실제 상태 확률이 아닙니다.",
        "현재 사용 가능",
    )
    state_frame = (
        profiles.groupby("predicted_state_label", observed=True)
        .size()
        .rename("users")
        .reset_index()
    )
    st.plotly_chart(
        retention_state_distribution(state_frame),
        width="stretch",
        key="home_state_distribution",
        config={"displayModeBar": False, "responsive": True},
    )

with flow_column:
    section_header(
        "운영 흐름",
        "현재 검토와 전략 선택까지 사용할 수 있습니다.",
    )
    operations_flow()

with st.expander(
    "행동 신호 상세 보기",
    icon=":material/analytics:",
    expanded=False,
):
    type_counts = profiles["core_signal"].value_counts()
    section_header(
        "규칙 기반 핵심 신호",
        "모델 클래스와 별도로 개인의 관찰 가능한 행동 변화를 요약합니다.",
    )
    signal_bars([(label, int(count)) for label, count in type_counts.items()])

render_warnings(data.warnings)
footer(data.data_mode)
