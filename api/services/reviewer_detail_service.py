"""리뷰어 상세(reviewer-details.json) 조회.

vw_reviewer_validation에서 읽는다 — vw_reviewer_work_queue와 달리 사후
검증값(target_review_count/target_active_months/retention_state/churn)이
포함된 뷰다. build_detail()의 "actual"(사후 검증, 화면에서 토글 뒤에 숨김)
섹션이 이 값을 쓰기 때문에 여기서는 명시적으로 이 뷰를 쓴다 — 운영 조회용
reviewer_service.py가 vw_reviewer_work_queue만 쓰는 것과 대비된다.
docs/ui/REACT_V04_DB_INTEGRATION_PLAN.md 5-2절 참고.

operator_decisions 쪽 8개 컬럼은 reviewer_service.py와 같은 이유로 여기서도
SELECT하지 않는다.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from shared.retention.frontend_serializer import build_detail
from shared.retention.profile_normalization import _normalize_profiles as normalize_profiles

MODEL_VERSION = "v05_05_dl"

_COLUMNS = """
    sample_id, user_id, comparison_year, selection_year, target_year,
    prior_activity_available,
    retained_score, weakened_score, stopped_score, priority_score,
    predicted_state, predicted_state_label, priority_rank,
    priority_top_percent, selected_for_crm,
    baseline_review_count, recent_review_count, review_count_decline_rate,
    baseline_active_months, recent_active_months, active_month_decline_rate,
    baseline_recency_days, recent_recency_days, recency_increase_days,
    baseline_mean_interval_days, recent_mean_interval_days,
    mean_interval_increase_days,
    baseline_unique_business_count, recent_unique_business_count,
    unique_business_decline_rate,
    target_review_count, target_active_months, retention_state, churn
"""


def get_reviewer_detail(engine: Engine, user_id: str) -> dict | None:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT {_COLUMNS} FROM vw_reviewer_validation "
                "WHERE model_version = :v AND user_id = :user_id"
            ),
            {"v": MODEL_VERSION, "user_id": user_id},
        ).mappings().all()

        if not rows:
            return None

        monthly_rows = conn.execute(
            text(
                """
                SELECT m.year_month, m.review_count, m.unique_business_count
                FROM reviewer_monthly_activity AS m
                JOIN cohort_samples AS c
                  ON c.model_version = m.model_version
                 AND c.sample_id = m.sample_id
                WHERE m.model_version = :v AND c.user_id = :user_id
                ORDER BY m.year_month
                """
            ),
            {"v": MODEL_VERSION, "user_id": user_id},
        ).all()

    monthly_activity = [
        {
            "month": year_month,
            "reviewCount": int(review_count),
            "uniqueBusinessCount": int(unique_business_count),
        }
        for year_month, review_count, unique_business_count in monthly_rows
    ]

    frame = pd.DataFrame([dict(row) for row in rows])
    frame = normalize_profiles(frame, model_version=MODEL_VERSION)

    detail = build_detail(frame.iloc[0])
    detail["monthlyActivity"] = monthly_activity
    return detail
