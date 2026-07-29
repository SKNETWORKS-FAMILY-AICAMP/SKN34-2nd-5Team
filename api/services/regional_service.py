"""콘텐츠 위험 / 권역별 화면(vw_regional_risk_summary) 조회.

app/src/data/regional.json 의 export_regional()과 필드가 1:1로 대응된다
(scripts/export_frontend_data.py:756). regional.json 자체는 6,533명
전원이 이미 권역이 배정된 v04 Test 표본 기준으로 만들어졌으므로, 여기서도
model_version='v04' 로 고정한다.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

MODEL_VERSION = "v04"
MINIMUM_REVIEWERS = 30


def get_regional_summary(engine: Engine) -> dict:
    with engine.connect() as conn:
        cohort_row = conn.execute(
            text(
                "SELECT comparison_year, selection_year FROM cohort_samples "
                "WHERE model_version = :v AND split_v04 = 'test' LIMIT 1"
            ),
            {"v": MODEL_VERSION},
        ).first()

        total_reviewers = conn.execute(
            text(
                "SELECT COUNT(*) FROM cohort_samples "
                "WHERE model_version = :v AND split_v04 = 'test'"
            ),
            {"v": MODEL_VERSION},
        ).scalar()

        covered_reviewers = conn.execute(
            text(
                "SELECT COUNT(*) FROM reviewer_region WHERE model_version = :v"
            ),
            {"v": MODEL_VERSION},
        ).scalar()

        if cohort_row is None or not covered_reviewers:
            return {
                "available": False,
                "regions": [],
                "minimumReviewers": MINIMUM_REVIEWERS,
            }

        rows = conn.execute(
            text(
                """
                SELECT
                    state, top_city, total_reviewers, retained_count,
                    weakened_count, stopped_count, high_risk_count,
                    crm_targets, below_minimum
                FROM vw_regional_risk_summary
                WHERE model_version = :v
                ORDER BY total_reviewers DESC
                """
            ),
            {"v": MODEL_VERSION},
        ).mappings().all()

    # 뷰의 high_risk_rate 컬럼은 정수 나눗셈이라 MySQL이 소수점 4자리로
    # 자른다(div_precision_increment 기본값). 이미 가져온 정수 카운트로
    # 여기서 다시 나눠 원본 export_frontend_data.py와 같은 float 정밀도를
    # 낸다. (팀원 공유 사항 — 뷰 자체를 CAST(... AS DOUBLE)로 바꾸면
    # 이 우회가 필요 없어진다.)
    regions = [
        {
            "region": row["state"],
            "topCity": row["top_city"] or "—",
            "reviewers": int(row["total_reviewers"]),
            "retained": int(row["retained_count"]),
            "weakened": int(row["weakened_count"]),
            "stopped": int(row["stopped_count"]),
            "highRisk": int(row["high_risk_count"]),
            "highRiskRate": (
                int(row["high_risk_count"]) / int(row["total_reviewers"])
                if row["total_reviewers"]
                else 0.0
            ),
            "crmTargets": int(row["crm_targets"]),
            "belowMinimum": bool(row["below_minimum"]),
        }
        for row in rows
    ]

    return {
        "available": True,
        "minimumReviewers": MINIMUM_REVIEWERS,
        "comparisonYear": int(cohort_row.comparison_year),
        "selectionYear": int(cohort_row.selection_year),
        "coveredReviewers": int(covered_reviewers),
        "totalReviewers": int(total_reviewers),
        "regions": regions,
    }
