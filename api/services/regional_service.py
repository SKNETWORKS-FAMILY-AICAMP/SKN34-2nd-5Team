"""콘텐츠 위험 / 권역별 화면(vw_regional_risk_summary) 조회.

app/src/data/regional.json 의 export_regional()과 필드가 1:1로 대응된다
(scripts/export_frontend_data.py:756).

모델 버전 상수를 두 개로 나눈다. `get_regional_summary`는
vw_regional_risk_summary(reviewer_region + model_predictions)를 읽어 예측
결과에 따라 바뀌므로 운영 중인 예측 모델(PREDICTION_MODEL_VERSION)을 따라간다.
`get_regional_radius`(reviewer_spatial_summary)와
`get_regional_campaign_restaurants`(reviewer_restaurant_recommendation)는
예측 모델과 무관한 지리·추천 파생 데이터라 v04에 고정한다 —
v05/database/ddl/017_add_recommendation_context.sql의 "모델 버전은 v04로
유지 — 예측 모델과 무관"과 같은 이유다.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from urllib.parse import quote_plus

import numpy as np
import pandas as pd

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from api.services.business_attribute_service import get_business_display_attributes
from api.services.business_photo_service import get_business_photos

PREDICTION_MODEL_VERSION = "v05_05_dl"
DERIVED_MODEL_VERSION = "v05_05_dl"
MINIMUM_REVIEWERS = 30
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _normalize_city(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _city_key(value: str) -> str:
    return value.strip().lower()


@lru_cache(maxsize=1)
def _load_region_coordinates() -> dict[tuple[str, str], tuple[float, float]]:
    """Use actual business coordinates as map markers for state-level regions."""
    path = PROJECT_ROOT / "data" / "processed" / "spatial" / "business_locations_v04.parquet"
    frame = pd.read_parquet(path, columns=["state", "city", "latitude", "longitude"])
    frame = frame.dropna(subset=["state", "city", "latitude", "longitude"])
    frame["city_key"] = frame["city"].astype(str).map(_normalize_city)
    grouped = frame.groupby(["state", "city_key"], as_index=False)[["latitude", "longitude"]].mean()
    coordinates = {
        (row.state, row.city_key): (float(row.latitude), float(row.longitude))
        for row in grouped.itertuples(index=False)
    }
    state_means = frame.groupby("state", as_index=False)[["latitude", "longitude"]].mean()
    coordinates.update(
        {
            (row.state, "__state__"): (float(row.latitude), float(row.longitude))
            for row in state_means.itertuples(index=False)
        }
    )
    return coordinates


def _region_coordinates(row: dict) -> dict:
    coordinates = _load_region_coordinates()
    latitude, longitude = coordinates.get(
        (row["state"], _normalize_city(row["top_city"] or "")),
        coordinates.get((row["state"], "__state__"), (None, None)),
    )
    return {"latitude": latitude, "longitude": longitude}


@lru_cache(maxsize=1)
def _load_business_coordinates() -> dict[str, tuple[float, float]]:
    path = PROJECT_ROOT / "data" / "processed" / "spatial" / "business_locations_v04.parquet"
    frame = pd.read_parquet(path, columns=["business_id", "latitude", "longitude"])
    frame = frame.dropna(subset=["business_id", "latitude", "longitude"])
    return {
        str(row.business_id): (float(row.latitude), float(row.longitude))
        for row in frame.itertuples(index=False)
    }


@lru_cache(maxsize=1)
def _load_business_core_info() -> dict[str, dict]:
    interim = PROJECT_ROOT / "data" / "interim"
    columns = ["business_id", "name", "city", "state", "stars", "review_count", "categories"]
    frame = pd.concat(
        [
            pd.read_parquet(interim / "restaurant_businesses.parquet", columns=columns),
            pd.read_parquet(interim / "additional_culinary_businesses_v02.parquet", columns=columns),
        ],
        ignore_index=True,
    ).drop_duplicates("business_id", keep="first")
    info = {}
    for row in frame.itertuples(index=False):
        primary_category = str(row.categories).split(",")[0].strip() if pd.notna(row.categories) else None
        info[str(row.business_id)] = {
            "name": row.name,
            "city": row.city,
            "state": row.state,
            "stars": float(row.stars) if pd.notna(row.stars) else None,
            "reviewCount": int(row.review_count) if pd.notna(row.review_count) else 0,
            "primaryCategory": primary_category,
        }
    return info


def _active_sponsors(
    engine: Engine, region: str, city_key: str | None = None, limit: int = 4
) -> list[dict]:
    with engine.connect() as connection:
        found = int(
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = 'business_sponsorships'"
                )
            ).scalar_one()
        )
        if not found:
            return []
        rows = connection.execute(
            text(
                """
                SELECT business_id, end_date
                FROM business_sponsorships
                WHERE region_state = :region
                  AND status IN ('scheduled', 'active', 'approved')
                  AND CURDATE() BETWEEN start_date AND end_date
                ORDER BY priority_tier ASC, start_date ASC
                """
            ),
            {"region": region},
        ).mappings().all()

    core_info = _load_business_core_info()
    if city_key is not None:
        rows = [
            row for row in rows
            if (info := core_info.get(str(row["business_id"]))) is not None
            and _city_key(str(info["city"])) == city_key
        ]
    rows = rows[:limit]
    coordinates = _load_business_coordinates()
    display_attributes = get_business_display_attributes(
        engine, [str(row["business_id"]) for row in rows]
    )
    business_photos = get_business_photos(
        engine, [str(row["business_id"]) for row in rows]
    )
    sponsors = []
    for row in rows:
        business_id = str(row["business_id"])
        info = core_info.get(business_id)
        if info is None:
            continue
        latitude, longitude = coordinates.get(business_id, (None, None))
        query = quote_plus(f'{info["name"]} {info["city"]} {info["state"]}')
        sponsors.append(
            {
                "businessId": business_id,
                "name": info["name"],
                "city": info["city"],
                "state": info["state"],
                "primaryCategory": info["primaryCategory"],
                "stars": info["stars"],
                "reviewCount": info["reviewCount"],
                "matchedReviewerCount": 0,
                "latitude": latitude,
                "longitude": longitude,
                "yelpSearchUrl": f"https://www.yelp.com/search?find_desc={query}",
                "displayAttributes": display_attributes.get(business_id),
                "photos": business_photos.get(business_id, []),
                "reviewSupplyChangeRate": None,
                "sponsored": True,
                "sponsorshipEndDate": row["end_date"].isoformat(),
            }
        )
    return sponsors


def get_regional_campaign_restaurants(
    engine: Engine,
    region: str,
    sample_ids: list[str],
    target_scope: str = "region",
    city_key: str | None = None,
) -> dict:
    """Aggregate already-derived individual recommendations for a campaign pool.

    The caller supplies the currently selected, client-side risk-type pool.
    This makes the restaurant candidates change with the campaign selection
    without reimplementing risk classification in SQL.
    """
    if target_scope not in {"region", "city"}:
        raise ValueError("Unsupported campaign target scope.")
    normalized_city = _city_key(city_key or "") or None
    if target_scope == "city" and normalized_city is None:
        raise ValueError("A city campaign requires a city key.")
    if target_scope == "region":
        normalized_city = None
    unique_sample_ids = list(dict.fromkeys(sample_ids))[:5000]
    if not unique_sample_ids:
        return {"available": False, "region": region, "restaurants": [], "sponsoredRestaurants": []}

    statement = text(
        """
        SELECT recommendation.business_id, recommendation.business_name,
               recommendation.city, recommendation.state,
               recommendation.primary_category, recommendation.stars,
               recommendation.review_count,
               COUNT(DISTINCT recommendation.sample_id) AS matched_reviewer_count,
               MIN(recommendation.recommendation_rank) AS best_rank,
               MAX(supply.yoy_review_change_rate) AS review_supply_change_rate
        FROM reviewer_restaurant_recommendation AS recommendation
        INNER JOIN reviewer_region AS reviewer_region
          ON reviewer_region.sample_id = recommendation.sample_id
         AND reviewer_region.model_version = recommendation.model_version
        LEFT JOIN business_review_supply AS supply
          ON supply.model_version = recommendation.model_version
         AND supply.business_id = recommendation.business_id
         AND supply.is_selection_year = 1
        WHERE recommendation.model_version = :model_version
          AND reviewer_region.state = :region
          AND (:target_scope = 'region' OR LOWER(TRIM(reviewer_region.top_city)) = :city_key)
          AND (:target_scope = 'region' OR LOWER(TRIM(recommendation.city)) = :city_key)
          AND recommendation.sample_id IN :sample_ids
        GROUP BY recommendation.business_id, recommendation.business_name,
                 recommendation.city, recommendation.state,
                 recommendation.primary_category, recommendation.stars,
                 recommendation.review_count
        ORDER BY matched_reviewer_count DESC, best_rank ASC, recommendation.review_count DESC
        LIMIT 12
        """
    ).bindparams(bindparam("sample_ids", expanding=True))
    with engine.connect() as connection:
        rows = connection.execute(
            statement,
            {
                "model_version": DERIVED_MODEL_VERSION,
                "region": region,
                "target_scope": target_scope,
                "city_key": normalized_city,
                "sample_ids": unique_sample_ids,
            },
        ).mappings().all()

    coordinates = _load_business_coordinates()
    display_attributes = get_business_display_attributes(
        engine, [str(row["business_id"]) for row in rows]
    )
    business_photos = get_business_photos(
        engine, [str(row["business_id"]) for row in rows]
    )
    restaurants = []
    for row in rows:
        latitude, longitude = coordinates.get(str(row["business_id"]), (None, None))
        query = quote_plus(f'{row["business_name"]} {row["city"]} {row["state"]}')
        restaurants.append(
            {
                "businessId": row["business_id"],
                "name": row["business_name"],
                "city": row["city"],
                "state": row["state"],
                "primaryCategory": row["primary_category"],
                "stars": float(row["stars"]),
                "reviewCount": int(row["review_count"]),
                "matchedReviewerCount": int(row["matched_reviewer_count"]),
                "latitude": latitude,
                "longitude": longitude,
                "yelpSearchUrl": f"https://www.yelp.com/search?find_desc={query}",
                "displayAttributes": display_attributes.get(str(row["business_id"])),
                "photos": business_photos.get(str(row["business_id"]), []),
                "reviewSupplyChangeRate": (
                    float(row["review_supply_change_rate"])
                    if row["review_supply_change_rate"] is not None
                    else None
                ),
                "sponsored": False,
            }
        )

    sponsors = _active_sponsors(engine, region, normalized_city)
    sponsor_ids = {sponsor["businessId"] for sponsor in sponsors}
    restaurants = [item for item in restaurants if item["businessId"] not in sponsor_ids]

    return {
        "available": bool(restaurants) or bool(sponsors),
        "region": region,
        "targetScope": target_scope,
        "cityKey": normalized_city,
        "restaurants": restaurants,
        "sponsoredRestaurants": sponsors,
    }


def get_regional_summary(engine: Engine) -> dict:
    with engine.connect() as conn:
        cohort_row = conn.execute(
            text(
                "SELECT comparison_year, selection_year FROM cohort_samples "
                "WHERE model_version = :v AND split_v04 = 'test' LIMIT 1"
            ),
            {"v": PREDICTION_MODEL_VERSION},
        ).first()

        total_reviewers = conn.execute(
            text(
                "SELECT COUNT(*) FROM cohort_samples "
                "WHERE model_version = :v AND split_v04 = 'test'"
            ),
            {"v": PREDICTION_MODEL_VERSION},
        ).scalar()

        covered_reviewers = conn.execute(
            text(
                "SELECT COUNT(*) FROM reviewer_region WHERE model_version = :v"
            ),
            {"v": PREDICTION_MODEL_VERSION},
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
            {"v": PREDICTION_MODEL_VERSION},
        ).mappings().all()

    # 뷰의 high_risk_rate 컬럼은 정수 나눗셈이라 MySQL이 소수점 4자리로
    # 자른다(div_precision_increment 기본값). 이미 가져온 정수 카운트로
    # 여기서 다시 나눠 원본 export_frontend_data.py와 같은 float 정밀도를
    # 낸다. (팀원 공유 사항 — 뷰 자체를 CAST(... AS DOUBLE)로 바꾸면
    # 이 우회가 필요 없어진다.)
    regions = [
        {
            "region": row["state"],
            **_region_coordinates(row),
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
            {"v": DERIVED_MODEL_VERSION},
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
