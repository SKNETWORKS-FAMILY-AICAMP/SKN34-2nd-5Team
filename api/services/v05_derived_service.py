"""Read-only API services for optional v05 G-1/G-2/G-4 DB tables.

The v05 tables are deployed separately. Until they exist, these functions
return an explicit unavailable contract instead of raising a SQL error, so the
current React application remains deployable during the handoff.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


MODEL_VERSION = "v04"
SELECTION_YEAR = 2018


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
                       search_radius_km, reason
                FROM reviewer_restaurant_recommendation
                WHERE model_version = :model_version AND sample_id = :sample_id
                ORDER BY recommendation_rank
                """
            ),
            {"model_version": MODEL_VERSION, "sample_id": sample.sample_id},
        ).mappings().all()

    return {
        "available": bool(rows),
        "reason": None if rows else "no_eligible_candidates",
        "sampleId": sample.sample_id,
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
                "reason": row["reason"],
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

    newcomers = {state: int(count) for state, count in newcomer_rows}
    return {
        "available": bool(supply_rows),
        "reason": None if supply_rows else "no_rows_for_selection_year",
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
            }
            for row in supply_rows
        ],
    }
