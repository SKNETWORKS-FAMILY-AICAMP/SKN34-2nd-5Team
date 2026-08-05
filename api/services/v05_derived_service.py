"""Read-only API services for optional v05 G-1/G-2/G-4 DB tables.

The v05 tables are deployed separately. Until they exist, these functions
return an explicit unavailable contract instead of raising a SQL error, so the
current React application remains deployable during the handoff.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from api.services.business_attribute_service import get_business_display_attributes
from api.services.business_photo_service import get_business_photos


MODEL_VERSION = "v05_05_dl"
SELECTION_YEAR = 2018
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEEKDAY_LABELS = {
    1: "월", 2: "화", 3: "수", 4: "목", 5: "금", 6: "토", 7: "일",
}


@lru_cache(maxsize=1)
def _recommendation_coordinates() -> dict[str, tuple[float, float]]:
    path = PROJECT_ROOT / "data" / "processed" / "spatial" / "business_locations_v04.parquet"
    frame = pd.read_parquet(path, columns=["business_id", "latitude", "longitude"])
    frame = frame.dropna(subset=["business_id", "latitude", "longitude"])
    return {
        str(row.business_id): (float(row.latitude), float(row.longitude))
        for row in frame.itertuples(index=False)
    }


def _tables_available(connection: Connection, table_names: tuple[str, ...]) -> bool:
    placeholders = ", ".join(f"'{name}'" for name in table_names)
    found = int(
        connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() "
                f"AND table_name IN ({placeholders})"
            )
        ).scalar_one()
    )
    return found == len(table_names)


def get_reviewer_recommendations(engine: Engine, user_id: str) -> dict | None:
    with engine.connect() as connection:
        sample = connection.execute(
            text(
                "SELECT sample_id FROM cohort_samples "
                "WHERE model_version = :model_version AND user_id = :user_id "
                "AND split_v04 = 'test' AND selection_year = :selection_year"
            ),
            {
                "model_version": MODEL_VERSION,
                "user_id": user_id,
                "selection_year": SELECTION_YEAR,
            },
        ).first()
        if sample is None:
            return None
        if not _tables_available(
            connection, ("reviewer_restaurant_recommendation",)
        ):
            return {
                "available": False,
                "reason": "database_not_loaded",
                "sampleId": sample.sample_id,
                "recommendations": [],
            }

        rows = connection.execute(
            text(
                """
                SELECT business_id, business_name, city, state, distance_km,
                       matched_categories, primary_category, stars,
                       review_count, recommendation_rank, radius_stage,
                       search_radius_km, observed_p90_radius_km,
                       local_p90_radius_km, travel_outlier_count,
                       activity_cluster_count, primary_cluster_business_count,
                       recommendation_version, reason
                FROM reviewer_restaurant_recommendation
                WHERE model_version = :model_version AND sample_id = :sample_id
                ORDER BY recommendation_rank
                """
            ),
            {"model_version": MODEL_VERSION, "sample_id": sample.sample_id},
        ).mappings().all()

    coordinates = _recommendation_coordinates()
    display_attributes = get_business_display_attributes(
        engine, [str(row["business_id"]) for row in rows]
    )
    business_photos = get_business_photos(
        engine, [str(row["business_id"]) for row in rows]
    )
    first_row = rows[0] if rows else None
    return {
        "available": bool(rows),
        "reason": None if rows else "no_eligible_candidates",
        "sampleId": sample.sample_id,
        "radiusContext": (
            {
                "observedP90RadiusKm": float(first_row["observed_p90_radius_km"]),
                "localP90RadiusKm": float(first_row["local_p90_radius_km"]),
                "primaryClusterP90RadiusKm": float(first_row["local_p90_radius_km"]),
                "travelOutlierCount": int(first_row["travel_outlier_count"]),
                "activityClusterCount": int(first_row["activity_cluster_count"]),
                "remoteRegionCount": max(0, int(first_row["activity_cluster_count"]) - 1),
                "primaryClusterBusinessCount": int(
                    first_row["primary_cluster_business_count"]
                ),
                "appliedSearchRadiusKm": float(first_row["search_radius_km"]),
                "radiusCapKm": 50.0,
                "radiusCapApplied": float(first_row["local_p90_radius_km"]) > 50.0,
                "multiRegionActivity": int(first_row["activity_cluster_count"]) > 1,
                "method": "primary_activity_cluster_50km",
                "recommendationVersion": first_row["recommendation_version"],
            }
            if first_row and first_row["local_p90_radius_km"] is not None
            else None
        ),
        "recommendations": [
            {
                "businessId": row["business_id"],
                "name": row["business_name"],
                "city": row["city"],
                "state": row["state"],
                "distanceKm": float(row["distance_km"]),
                "matchedCategories": [
                    label.strip()
                    for label in row["matched_categories"].split(",")
                    if label.strip()
                ],
                "primaryCategory": row["primary_category"],
                "stars": float(row["stars"]),
                "reviewCount": int(row["review_count"]),
                "rank": int(row["recommendation_rank"]),
                "radiusStage": row["radius_stage"],
                "searchRadiusKm": float(row["search_radius_km"]),
                "distanceBand": (
                    "core"
                    if float(row["distance_km"]) <= float(row["local_p90_radius_km"])
                    else "expanded"
                ),
                "reason": row["reason"],
                "latitude": coordinates.get(str(row["business_id"]), (None, None))[0],
                "longitude": coordinates.get(str(row["business_id"]), (None, None))[1],
                "yelpSearchUrl": "https://www.yelp.com/search?find_desc="
                + quote_plus(f'{row["business_name"]} {row["city"]} {row["state"]}'),
                "displayAttributes": display_attributes.get(str(row["business_id"])),
                "photos": business_photos.get(str(row["business_id"]), []),
            }
            for row in rows
        ],
    }


def get_regional_derived_context(
    engine: Engine, selection_year: int = SELECTION_YEAR
) -> dict:
    tables = ("regional_newcomer", "regional_review_supply")
    with engine.connect() as connection:
        if not _tables_available(connection, tables):
            return {
                "available": False,
                "reason": "database_not_loaded",
                "selectionYear": selection_year,
                "regions": [],
            }

        supply_rows = connection.execute(
            text(
                """
                SELECT state, review_count, active_reviewer_count,
                       active_business_count, previous_year_review_count,
                       yoy_review_change, yoy_review_change_rate
                FROM regional_review_supply
                WHERE model_version = :model_version
                  AND activity_year = :selection_year
                ORDER BY state
                """
            ),
            {"model_version": MODEL_VERSION, "selection_year": selection_year},
        ).mappings().all()
        newcomer_rows = connection.execute(
            text(
                """
                SELECT state, new_power_reviewers
                FROM regional_newcomer
                WHERE model_version = :model_version
                  AND selection_year = :selection_year
                """
            ),
            {"model_version": MODEL_VERSION, "selection_year": selection_year},
        ).all()
        weekday_rows = []
        if _tables_available(connection, ("regional_weekday_pattern",)):
            weekday_rows = connection.execute(
                text(
                    """
                    SELECT state, iso_weekday, review_count
                    FROM regional_weekday_pattern
                    WHERE model_version = :model_version
                      AND activity_year = :selection_year
                    ORDER BY state, iso_weekday
                    """
                ),
                {"model_version": MODEL_VERSION, "selection_year": selection_year},
            ).mappings().all()

    newcomers = {state: int(count) for state, count in newcomer_rows}
    weekday_by_region: dict[str, list[dict]] = {}
    for row in weekday_rows:
        weekday_by_region.setdefault(str(row["state"]), []).append(
            {
                "isoWeekday": int(row["iso_weekday"]),
                "label": WEEKDAY_LABELS[int(row["iso_weekday"])],
                "reviewCount": int(row["review_count"]),
            }
        )

    global_by_day = {
        day: sum(
            item["reviewCount"]
            for rows in weekday_by_region.values()
            for item in rows
            if item["isoWeekday"] == day
        )
        for day in WEEKDAY_LABELS
    }

    def pattern_payload(state: str) -> dict | None:
        days = weekday_by_region.get(state, [])
        if len(days) != 7:
            return None

        def intensity(counts: dict[int, int]) -> tuple[float, float, float]:
            weekday_average = sum(counts[day] for day in range(1, 6)) / 5
            weekend_average = sum(counts[day] for day in (6, 7)) / 2
            denominator = weekday_average + weekend_average
            normalized = weekend_average / denominator if denominator else 0.0
            return weekday_average, weekend_average, normalized

        counts = {item["isoWeekday"]: item["reviewCount"] for item in days}
        weekday_average, weekend_average, weekend_intensity = intensity(counts)
        _, _, baseline_intensity = intensity(global_by_day)
        peak_day = max(days, key=lambda item: (item["reviewCount"], -item["isoWeekday"]))
        return {
            "days": days,
            "weekdayDailyAverage": round(weekday_average, 1),
            "weekendDailyAverage": round(weekend_average, 1),
            "weekendIntensity": round(weekend_intensity, 4),
            "baselineWeekendIntensity": round(baseline_intensity, 4),
            "baselineDeltaPercentagePoints": round(
                (weekend_intensity - baseline_intensity) * 100, 1
            ),
            "peakDay": peak_day["label"],
            "calculationNote": "2018년 통합 미식 리뷰의 요일별 일평균 강도",
        }

    return {
        "available": bool(supply_rows),
        "reason": None if supply_rows else "no_rows_for_selection_year",
        "modelVersion": MODEL_VERSION,
        "businessScope": "restaurants_and_selected_culinary",
        "selectionYear": selection_year,
        "regions": [
            {
                "region": row["state"],
                "reviewCount": int(row["review_count"]),
                "activeReviewers": int(row["active_reviewer_count"]),
                "activeBusinesses": int(row["active_business_count"]),
                "previousYearReviewCount": (
                    int(row["previous_year_review_count"])
                    if row["previous_year_review_count"] is not None
                    else None
                ),
                "reviewSupplyChange": (
                    int(row["yoy_review_change"])
                    if row["yoy_review_change"] is not None
                    else None
                ),
                "reviewSupplyChangeRate": (
                    float(row["yoy_review_change_rate"])
                    if row["yoy_review_change_rate"] is not None
                    else None
                ),
                "newPowerReviewers": newcomers.get(row["state"], 0),
                "weekdayPattern": pattern_payload(str(row["state"])),
            }
            for row in supply_rows
        ],
    }
