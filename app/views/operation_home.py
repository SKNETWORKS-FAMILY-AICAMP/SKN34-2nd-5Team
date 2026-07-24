from __future__ import annotations

import pandas as pd
import streamlit as st

from core.charts import tier_distribution
from core.components import (
    footer,
    metric_strip,
    operations_flow,
    page_intro,
    policy_brief,
    priority_queue,
    render_warnings,
    section_header,
    signal_bars,
)
from core.data import load_app_data


data = load_app_data()
profiles = data.reviewer_profiles.copy()
policy = data.primary_policy.iloc[0] if not data.primary_policy.empty else pd.Series()

total_reviewers = len(profiles)
crm_users = int(policy.get("target_users", profiles["crm_target"].sum()))
captured_users = int(
    policy.get(
        "true_positive",
        profiles.loc[profiles["crm_target"].eq(1), "churn"].sum(),
    )
)
recall = float(policy.get("recall", 0.0))
lift = float(policy.get("lift", 0.0))
urgent_users = int(profiles["risk_tier"].eq("긴급 관리").sum())

page_intro(
    "Operations briefing · Test 2019",
    "오늘의 리텐션 운영",
    "우선순위가 높은 신호를 검토하고 다음 행동으로 바로 이동합니다.",
    ["현재 데모에서 사용 가능" if data.data_mode == "demo" else "현재 사용 가능"],
)
render_warnings(data.warnings)

metric_strip(
    [
        ("전체 평가 리뷰어", f"{total_reviewers:,}명", "2019 Test cohort"),
        ("CRM 검토 대상", f"{crm_users:,}명", "위험 점수 상위 20%"),
        ("실제 이탈 포착", f"{captured_users:,}명", f"Recall@20 · {recall:.2%}"),
        ("무작위 대비 효율", f"{lift:.2f}×", "Lift@20"),
    ]
)

queue_column, brief_column = st.columns([1.68, 0.62], gap="large")
with queue_column:
    section_header(
        "우선 검토 큐",
        "행동 변화가 큰 순서입니다. 행을 선택하면 Reviewer 360으로 이동합니다.",
        "현재 사용 가능",
    )
    queue = profiles.nsmallest(6, "risk_rank")
    priority_queue(
        [
            {
                "rank": f"{int(row.risk_rank):02d}",
                "user_id": str(row.user_id),
                "risk_type": str(row.risk_type),
                "change": (
                    f"활동 월 {int(row.baseline_active_months)}"
                    f" → {int(row.recent_active_months)}개월"
                ),
                "before_value": float(row.baseline_active_months),
                "after_value": float(row.recent_active_months),
                "action": str(row.recommended_action),
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
    section_header("이번 운영 브리프", "검증된 정책 기준의 실제 수치입니다.")
    policy_brief(
        crm_users=crm_users,
        urgent_users=urgent_users,
        captured_users=captured_users,
        recall=recall,
    )

signal_counts = [
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
]

signal_column, flow_column = st.columns([1.2, 1], gap="large")
with signal_column:
    section_header(
        "어떤 신호가 늘고 있나",
        "프로필 데이터에서 직접 집계한 행동 변화입니다.",
        "현재 사용 가능",
    )
    signal_bars(signal_counts)

with flow_column:
    section_header(
        "운영 흐름",
        "현재 검토와 전략 선택까지 사용할 수 있습니다.",
    )
    operations_flow()

with st.expander(
    "운영 세그먼트 상세 보기",
    icon=":material/analytics:",
    expanded=False,
):
    detail_left, detail_right = st.columns([1, 1], gap="large")
    with detail_left:
        type_counts = profiles["risk_type"].value_counts()
        section_header("규칙 기반 위험 유형", "운영 설명을 위한 분류입니다.")
        signal_bars(
            [(risk_type, int(count)) for risk_type, count in type_counts.items()]
        )
    with detail_right:
        st.plotly_chart(
            tier_distribution(data.risk_tiers),
            width="stretch",
            key="home_tier_distribution",
        )

footer(data.data_mode)
