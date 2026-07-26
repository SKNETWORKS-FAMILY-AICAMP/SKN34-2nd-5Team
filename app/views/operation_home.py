from __future__ import annotations

import pandas as pd
import streamlit as st

from core.components import (
    empty_state,
    footer,
    policy_panel,
    priority_queue,
    render_warnings,
    status_badge,
)
from core.data import load_app_data
from core.decisions import get_decisions
from core.formatters import percent, signed_phrase


data = load_app_data()
profiles = data.reviewer_profiles.copy()
policy = data.primary_policy.iloc[0] if not data.primary_policy.empty else pd.Series()

target_users = int(policy.get("target_users", profiles["crm_target"].sum()))
captured_users = int(policy.get("status_loss_captured", 0))
precision = float(policy.get("status_loss_precision", 0.0))
recall = float(policy.get("status_loss_recall", 0.0))
lift = float(policy.get("status_loss_lift", 0.0))
recall_ceiling = (target_users / (captured_users / recall)) if recall else 0.0

predicted_counts = profiles["predicted_state"].value_counts()
weakened_total = int(predicted_counts.get(1, 0))
stopped_total = int(predicted_counts.get(2, 0))

decisions = get_decisions()
processed_ids = {str(uid) for uid in decisions.keys()}
pending_pool = profiles.loc[
    profiles["crm_target"].eq(1) & ~profiles["user_id"].astype(str).isin(processed_ids)
].sort_values("priority_rank")
queue_df = pending_pool.head(5)
completed_count = len(processed_ids)

status_label = "현재 데모에서 사용 가능" if data.data_mode == "demo" else "현재 사용 가능"
st.html(
    f"""
    <div class="rr-hero-head">
      <div>
        <div class="rr-eyebrow">OPERATIONS · V03</div>
        <div class="rr-title">우선 대응 대상 리뷰어</div>
        <p class="rr-copy">통합 우선순위 상위 20% · {target_users:,}명</p>
      </div>
      <div class="rr-hero-badge-col">
        {status_badge(status_label)}
        <div class="rr-snapshot-note">Test 2019 스냅샷 기준</div>
      </div>
    </div>
    """
)

queue_column, policy_column = st.columns([1.7, 1.0], gap="large")
with queue_column:
    st.html(
        f"""
        <div class="rr-qhead">
          <strong>이번 세션 우선 검토</strong>
          <span>{len(queue_df)}명 표시 · 통합 검토 대상 {target_users:,}명 중 · {completed_count}명 판단 완료</span>
        </div>
        """
    )
    if queue_df.empty:
        empty_state(
            "이번 세션 검토를 모두 마쳤습니다",
            "리뷰어 관리에서 전체 대상을 다시 확인할 수 있습니다.",
            "현재 사용 가능",
        )
    else:
        rows = []
        for row in queue_df.itertuples():
            change_text = (
                f"리뷰 수 {int(row.baseline_review_count)}건 → {int(row.recent_review_count)}건 · "
                + signed_phrase(
                    row.review_count_decline_rate,
                    percent,
                    when_positive="감소",
                    when_negative="증가",
                )
            )
            rows.append(
                {
                    "user_id": str(row.user_id),
                    "model_judgment": str(row.model_judgment),
                    "change_text": change_text,
                    "action": str(row.recommended_review),
                }
            )
        priority_queue(rows)
    if st.button(
        "리뷰어 관리에서 전체 대상 보기",
        type="primary",
        icon=":material/arrow_forward:",
        key="primary_action",
        width="stretch",
    ):
        st.session_state["reviewer_workspace_mode"] = "list"
        st.switch_page("views/risk_queue.py")

with policy_column:
    policy_panel(
        target_users=target_users,
        captured_users=captured_users,
        precision=precision,
        recall=recall,
        recall_ceiling=recall_ceiling,
        lift=lift,
        weakened_total=weakened_total,
        stopped_total=stopped_total,
    )

render_warnings(data.warnings)
footer(data.data_mode)
