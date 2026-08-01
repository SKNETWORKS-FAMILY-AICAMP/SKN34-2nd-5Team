"""콘텐츠 위험 / 권역별 화면(vw_regional_risk_summary) 조회.

app/src/data/regional.json 의 export_regional()과 필드가 1:1로 대응된다
(scripts/export_frontend_data.py:756). regional.json 자체는 6,533명
전원이 이미 권역이 배정된 v04 Test 표본 기준으로 만들어졌으므로, 여기서도
model_version='v04' 로 고정한다.
"""
from __future__ import annotations

import numpy as np

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


# 권역별 탐방 반경 분포 (work-spec A-7 / G-3). MySQL 8에는 내장
# PERCENTILE_CONT가 없어서, 권역별 원시 p90_radius_km 값을 그대로 가져와
# 사분위는 Python에서 계산한다 — vw_regional_risk_summary가 highRiskRate
# 정밀도를 여기서 다시 계산하는 것과 같은 이유(주석 참고).
#
# 반경은 위험 지표가 아니라 캠페인 범위 근거로만 쓴다 — 05_feature_
# validation_report.md §7에서 위험 예측 피처로 채택되지 않았다. 여기서
# retained/stopped 코호트 중앙값(14.29km/10.31km)을 다시 계산하지 않는
# 것도 같은 이유다 — 그건 실제 사후 상태 기준 검증 리포트 수치이고,
# predicted_state로 재계산하면 예측과 실제 결과를 섞는 것이 된다. 프런트는
# 그 두 수치를 검증 리포트 원문 값으로 고정 표시한다.
def get_regional_radius(engine: Engine) -> dict:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT state, p90_radius_km FROM vw_reviewer_regional_radius "
                "WHERE model_version = :v"
            ),
            {"v": MODEL_VERSION},
        ).all()

    by_state: dict[str, list[float]] = {}
    for state, radius_km in rows:
        by_state.setdefault(state, []).append(float(radius_km))

    regions = []
    for state, values in by_state.items():
        n = len(values)
        # Match the continuous percentile policy used by the DuckDB pipeline.
        q1, median, q3 = np.quantile(values, [0.25, 0.50, 0.75], method="linear")
        regions.append(
            {
                "region": state,
                "reviewers": n,
                "medianP90RadiusKm": round(median, 1),
                "q1P90RadiusKm": round(q1, 1),
                "q3P90RadiusKm": round(q3, 1),
                "belowMinimum": n < MINIMUM_REVIEWERS,
            }
        )

    regions.sort(key=lambda item: item["medianP90RadiusKm"])
    return {
        "available": bool(regions),
        "minimumReviewers": MINIMUM_REVIEWERS,
        "totalReviewers": sum(item["reviewers"] for item in regions),
        "excludedReviewers": 0,
        "regions": regions,
    }
