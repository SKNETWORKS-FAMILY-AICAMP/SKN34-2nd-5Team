"""Read-only city operating context for the v05 review-supply command center."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


MODEL_VERSION = "v04"
SELECTION_YEAR = 2018
MIN_ACTIVE_REVIEWERS = 30
MIN_ANNUAL_REVIEWS = 100
MIN_MAP_RADIUS_KM = 10.0
MAX_MAP_RADIUS_KM = 40.0


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


def _supply_status(rate: float | None, minimum_sample_met: bool) -> str:
    if not minimum_sample_met or rate is None:
        return "insufficient"
    if rate <= -0.15:
        return "strong_decline"
    if rate < -0.05:
        return "decline"
    if rate <= 0.05:
        return "stable"
    if rate < 0.15:
        return "growth"
    return "strong_growth"


def _volume_thresholds(rows: list[dict]) -> tuple[int, int]:
    counts = sorted(
        int(row["review_count"])
        for row in rows
        if bool(row["minimum_sample_met"])
    )
    if not counts:
        return (0, 0)
    return (counts[len(counts) // 3], counts[(len(counts) * 2) // 3])


def _volume_band(value: int, thresholds: tuple[int, int]) -> str:
    lower, upper = thresholds
    if value <= lower:
        return "small"
    if value <= upper:
        return "medium"
    return "large"


def get_city_operating_context(
    engine: Engine, selection_year: int = SELECTION_YEAR
) -> dict:
    tables = (
        "city_review_supply",
        "city_newcomer",
        "regional_review_supply",
        "regional_newcomer",
    )
    with engine.connect() as connection:
        if not _tables_available(connection, tables):
            return {
                "available": False,
                "reason": "database_not_loaded",
                "selectionYear": selection_year,
                "cities": [],
            }
        rows = [
            dict(row)
            for row in connection.execute(
                text(
                    """
                    SELECT
                        supply.state,
                        supply.city_key,
                        supply.city,
                        supply.center_latitude,
                        supply.center_longitude,
                        supply.p90_radius_km,
                        supply.review_count,
                        supply.active_reviewer_count,
                        supply.active_business_count,
                        supply.previous_year_review_count,
                        supply.yoy_review_change,
                        supply.yoy_review_change_rate,
                        supply.minimum_sample_met,
                        COALESCE(current_entry.new_power_reviewers, 0)
                            AS new_power_reviewers,
                        COALESCE(previous_entry.new_power_reviewers, 0)
                            AS previous_year_new_power_reviewers,
                        COALESCE(crm.core_reviewers, 0) AS core_reviewers,
                        COALESCE(crm.crm_targets, 0) AS crm_targets
                    FROM city_review_supply AS supply
                    LEFT JOIN city_newcomer AS current_entry
                      ON current_entry.model_version = supply.model_version
                     AND current_entry.selection_year = supply.activity_year
                     AND current_entry.state = supply.state
                     AND current_entry.city_key = supply.city_key
                    LEFT JOIN city_newcomer AS previous_entry
                      ON previous_entry.model_version = supply.model_version
                     AND previous_entry.selection_year = supply.activity_year - 1
                     AND previous_entry.state = supply.state
                     AND previous_entry.city_key = supply.city_key
                    LEFT JOIN (
                        SELECT
                            region.state,
                            LOWER(TRIM(region.top_city)) AS city_key,
                            COUNT(*) AS core_reviewers,
                            SUM(CASE WHEN queue.selected_for_crm = 1 THEN 1 ELSE 0 END)
                                AS crm_targets
                        FROM vw_reviewer_work_queue AS queue
                        INNER JOIN reviewer_region AS region
                          ON region.model_version = queue.model_version
                         AND region.sample_id = queue.sample_id
                        WHERE queue.model_version = :model_version
                          AND queue.selection_year = :selection_year
                        GROUP BY region.state, LOWER(TRIM(region.top_city))
                    ) AS crm
                      ON crm.state = supply.state
                     AND crm.city_key = supply.city_key
                    WHERE supply.model_version = :model_version
                      AND supply.activity_year = :selection_year
                    ORDER BY supply.state, supply.city
                    """
                ),
                {
                    "model_version": MODEL_VERSION,
                    "selection_year": selection_year,
                },
            ).mappings()
        ]
        region_rows = [
            dict(row)
            for row in connection.execute(
                text(
                    """
                    SELECT
                        supply.state,
                        supply.review_count,
                        supply.active_reviewer_count,
                        supply.active_business_count,
                        supply.previous_year_review_count,
                        supply.yoy_review_change,
                        supply.yoy_review_change_rate,
                        COALESCE(current_entry.new_power_reviewers, 0)
                            AS new_power_reviewers,
                        COALESCE(previous_entry.new_power_reviewers, 0)
                            AS previous_year_new_power_reviewers,
                        COALESCE(crm.core_reviewers, 0) AS core_reviewers,
                        COALESCE(crm.crm_targets, 0) AS crm_targets
                    FROM regional_review_supply AS supply
                    LEFT JOIN regional_newcomer AS current_entry
                      ON current_entry.model_version = supply.model_version
                     AND current_entry.selection_year = supply.activity_year
                     AND current_entry.state = supply.state
                    LEFT JOIN regional_newcomer AS previous_entry
                      ON previous_entry.model_version = supply.model_version
                     AND previous_entry.selection_year = supply.activity_year - 1
                     AND previous_entry.state = supply.state
                    LEFT JOIN (
                        SELECT
                            region.state,
                            COUNT(*) AS core_reviewers,
                            SUM(CASE WHEN queue.selected_for_crm = 1 THEN 1 ELSE 0 END)
                                AS crm_targets
                        FROM vw_reviewer_work_queue AS queue
                        INNER JOIN reviewer_region AS region
                          ON region.model_version = queue.model_version
                         AND region.sample_id = queue.sample_id
                        WHERE queue.model_version = :model_version
                          AND queue.selection_year = :selection_year
                        GROUP BY region.state
                    ) AS crm
                      ON crm.state = supply.state
                    WHERE supply.model_version = :model_version
                      AND supply.activity_year = :selection_year
                    ORDER BY supply.state
                    """
                ),
                {
                    "model_version": MODEL_VERSION,
                    "selection_year": selection_year,
                },
            ).mappings()
        ]

    thresholds = _volume_thresholds(rows)
    eligible_rows = [
        row
        for row in rows
        if bool(row["minimum_sample_met"])
        and row["yoy_review_change_rate"] is not None
    ]
    supply_ranked = sorted(
        eligible_rows,
        key=lambda row: (float(row["yoy_review_change_rate"]), row["state"], row["city_key"]),
    )
    supply_ranks = {
        (row["state"], row["city_key"]): index + 1
        for index, row in enumerate(supply_ranked)
    }
    core_ranked = sorted(
        eligible_rows,
        key=lambda row: (
            -int(row["crm_targets"]),
            float(row["yoy_review_change_rate"]),
            -int(row["review_count"]),
            row["state"],
            row["city_key"],
        ),
    )
    core_ranks = {
        (row["state"], row["city_key"]): index + 1
        for index, row in enumerate(core_ranked)
    }
    newcomer_ranked = sorted(
        eligible_rows,
        key=lambda row: (
            -int(row["new_power_reviewers"]),
            float(row["yoy_review_change_rate"]),
            -int(row["review_count"]),
            row["state"],
            row["city_key"],
        ),
    )
    newcomer_ranks = {
        (row["state"], row["city_key"]): index + 1
        for index, row in enumerate(newcomer_ranked)
    }

    cities = []
    for row in rows:
        review_rate = (
            float(row["yoy_review_change_rate"])
            if row["yoy_review_change_rate"] is not None
            else None
        )
        current_newcomers = int(row["new_power_reviewers"])
        previous_newcomers = int(row["previous_year_new_power_reviewers"])
        newcomer_change = current_newcomers - previous_newcomers
        newcomer_change_rate = (
            newcomer_change / previous_newcomers
            if previous_newcomers > 0
            else None
        )
        minimum_sample_met = bool(row["minimum_sample_met"])
        p90_radius = float(row["p90_radius_km"])
        cities.append(
            {
                "state": row["state"],
                "cityKey": row["city_key"],
                "city": row["city"],
                "latitude": float(row["center_latitude"]),
                "longitude": float(row["center_longitude"]),
                "p90RadiusKm": p90_radius,
                "displayRadiusKm": min(
                    MAX_MAP_RADIUS_KM, max(MIN_MAP_RADIUS_KM, p90_radius)
                ),
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
                "reviewSupplyChangeRate": review_rate,
                "newPowerReviewers": current_newcomers,
                "previousYearNewPowerReviewers": previous_newcomers,
                "newPowerReviewerChange": newcomer_change,
                "newPowerReviewerChangeRate": newcomer_change_rate,
                "coreReviewers": int(row["core_reviewers"]),
                "crmTargets": int(row["crm_targets"]),
                "minimumSampleMet": minimum_sample_met,
                "supplyStatus": _supply_status(review_rate, minimum_sample_met),
                "supplyVolumeBand": _volume_band(int(row["review_count"]), thresholds),
                "priorityRank": supply_ranks.get((row["state"], row["city_key"])),
                "supplyRank": supply_ranks.get((row["state"], row["city_key"])),
                "coreReviewerRank": core_ranks.get((row["state"], row["city_key"])),
                "newcomerRank": newcomer_ranks.get((row["state"], row["city_key"])),
            }
        )

    city_counts: dict[str, dict[str, int]] = {}
    for city in cities:
        state_counts = city_counts.setdefault(
            city["state"], {"total": 0, "eligible": 0}
        )
        state_counts["total"] += 1
        state_counts["eligible"] += int(city["minimumSampleMet"])

    eligible_region_rows = [
        row for row in region_rows if row["yoy_review_change_rate"] is not None
    ]
    region_supply_ranked = sorted(
        eligible_region_rows,
        key=lambda row: (float(row["yoy_review_change_rate"]), row["state"]),
    )
    region_core_ranked = sorted(
        eligible_region_rows,
        key=lambda row: (
            -int(row["crm_targets"]),
            float(row["yoy_review_change_rate"]),
            row["state"],
        ),
    )
    region_newcomer_ranked = sorted(
        eligible_region_rows,
        key=lambda row: (
            -int(row["new_power_reviewers"]),
            float(row["yoy_review_change_rate"]),
            row["state"],
        ),
    )
    region_supply_ranks = {
        row["state"]: index + 1 for index, row in enumerate(region_supply_ranked)
    }
    region_core_ranks = {
        row["state"]: index + 1 for index, row in enumerate(region_core_ranked)
    }
    region_newcomer_ranks = {
        row["state"]: index + 1 for index, row in enumerate(region_newcomer_ranked)
    }

    regions = []
    for row in region_rows:
        current_newcomers = int(row["new_power_reviewers"])
        previous_newcomers = int(row["previous_year_new_power_reviewers"])
        newcomer_change = current_newcomers - previous_newcomers
        newcomer_change_rate = (
            newcomer_change / previous_newcomers
            if previous_newcomers > 0
            else None
        )
        counts = city_counts.get(row["state"], {"total": 0, "eligible": 0})
        regions.append(
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
                "newPowerReviewers": current_newcomers,
                "previousYearNewPowerReviewers": previous_newcomers,
                "newPowerReviewerChange": newcomer_change,
                "newPowerReviewerChangeRate": newcomer_change_rate,
                "coreReviewers": int(row["core_reviewers"]),
                "crmTargets": int(row["crm_targets"]),
                "cityCount": counts["total"],
                "eligibleCityCount": counts["eligible"],
                "supplyRank": region_supply_ranks.get(row["state"]),
                "coreReviewerRank": region_core_ranks.get(row["state"]),
                "newcomerRank": region_newcomer_ranks.get(row["state"]),
            }
        )

    return {
        "available": bool(cities),
        "reason": None if cities else "no_rows_for_selection_year",
        "modelVersion": MODEL_VERSION,
        "comparisonYear": selection_year - 1,
        "selectionYear": selection_year,
        "minimumSample": {
            "activeReviewers": MIN_ACTIVE_REVIEWERS,
            "annualReviews": MIN_ANNUAL_REVIEWS,
        },
        "mapRadiusKm": {"minimum": MIN_MAP_RADIUS_KM, "maximum": MAX_MAP_RADIUS_KM},
        "eligibleCityCount": len(eligible_rows),
        "totalCityCount": len(cities),
        "eligibleRegionCount": len(eligible_region_rows),
        "volumeThresholds": {"small": thresholds[0], "medium": thresholds[1]},
        "regions": regions,
        "cities": cities,
    }
