"""리뷰어 관리(reviewers.json) 조회.

vw_reviewer_work_queue에서 운영 데이터를 읽고, build_row()가 기대하는
스키마(risk_type/core_signal/model_judgment/crm_target_label 등 파생
컬럼 포함)를 만들기 위해 shared.retention.profile_normalization의
_normalize_profiles를 거친다. archive/core는 거치지 않는다.

vw_reviewer_work_queue는 operator_decisions를 LEFT JOIN하지만, 그 8개
컬럼(decision_id, manager_decision, risk_type, model_judgment,
decision_reason, decision_owner, decided_at, playbook_id, review_due_at)은
관리자 판단 저장이 v05로 유예된 상태라 아예 SELECT하지 않는다 — React는
이 값을 localStorage에서 읽으므로, API가 내려주면 화면에서 그 상태를
덮어써 버리는 사고를 원천 차단한다.
docs/ui/REACT_V04_DB_INTEGRATION_PLAN.md 6-1절 "이번 작업에서의 주의" 참고.

reviewer_region_history는 2010~2018년 전체 이력(37,953행)이 model_version='v04'
로만 적재되어 있다. v05_05_dl의 cohort_samples는 2018년 Test 코호트 6,533명뿐이라
FK(reviewer_region_history.(model_version, sample_id) -> cohort_samples)가
과거 연도 이력을 v05_05_dl로 복제 적재하는 것 자체를 막는다. 그래서 신규 유입
판정(첫 파워 리뷰어 진입연도)에 쓰는 이 서브쿼리만 model_version을 'v04'로
고정한다 — regional_newcomer를 항상 model_version='v04'로 조회하는
v05_derived_service.py와 같은 패턴("v04 정의를 바꾸지 않는 파생 데이터").

`risk_type`이라는 이름이 operator_decisions에도 있어 혼동하기 쉬운데,
아래 쿼리는 그 컬럼을 아예 선택하지 않으므로 enrich_profiles()가 계산하는
risk_type(리뷰어 위험유형 분류)만 남는다.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from shared.retention.frontend_serializer import build_row
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
    unique_business_decline_rate
"""


def get_reviewers(engine: Engine) -> list[dict]:
    queue_columns = ", ".join(
        f"queue.{column.strip()}" for column in _COLUMNS.split(",") if column.strip()
    )
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT {queue_columns}, region.state AS region_state, region.top_city, "
                "entry.first_selection_year AS first_power_year "
                "FROM vw_reviewer_work_queue AS queue "
                "LEFT JOIN reviewer_region AS region "
                "ON region.sample_id = queue.sample_id AND region.model_version = :v "
                "LEFT JOIN reviewer_operating_entry AS entry "
                "ON entry.model_version = queue.model_version "
                "AND entry.sample_id = queue.sample_id "
                "WHERE queue.model_version = :v"
            ),
            {"v": MODEL_VERSION},
        ).mappings().all()

    frame = pd.DataFrame([dict(row) for row in rows])
    frame = normalize_profiles(frame, model_version=MODEL_VERSION)
    frame = frame.sort_values("priority_rank")

    serialized = []
    for _, row in frame.iterrows():
        item = build_row(row)
        item["region"] = row.get("region_state") or None
        item["topCity"] = row.get("top_city") or None
        first_power_year = row.get("first_power_year")
        item["firstPowerYear"] = (
            int(first_power_year) if pd.notna(first_power_year) else None
        )
        item["isNewcomer"] = bool(
            pd.notna(first_power_year)
            and int(first_power_year) == int(row["selection_year"])
        )
        serialized.append(item)
    return serialized
