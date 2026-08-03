"""Build city-level review-supply and newcomer operating artifacts for v05.

City means the location of the reviewed restaurant, never a reviewer's home.
The supply artifact counts all eligible restaurant reviews through the v04
selection year. Newcomers reuse the published v04 reviewer-region history so
the existing cohort and tie-breaking rules remain unchanged.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
MODEL_VERSION = "v04"
MIN_ACTIVE_REVIEWERS = 30
MIN_ANNUAL_REVIEWS = 100


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def normalize_city(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower()


def build_supply(first_year: int, last_year: int) -> pd.DataFrame:
    interim = ROOT / "data" / "interim"
    processed = ROOT / "data" / "processed"
    reviews = interim / "restaurant_reviews.parquet"
    businesses = interim / "restaurant_businesses.parquet"
    region_source = processed / "reviewer_region_v04.parquet"

    connection = duckdb.connect()
    frame = connection.execute(
        f"""
        WITH allowed_states AS (
            SELECT DISTINCT state
            FROM read_parquet('{sql_path(region_source)}')
        ), business_city AS (
            SELECT
                business.business_id,
                business.state,
                LOWER(TRIM(business.city)) AS city_key,
                TRIM(business.city) AS city,
                CAST(business.latitude AS DOUBLE) AS latitude,
                CAST(business.longitude AS DOUBLE) AS longitude
            FROM read_parquet('{sql_path(businesses)}') AS business
            INNER JOIN allowed_states USING (state)
            WHERE business.city IS NOT NULL
              AND TRIM(business.city) <> ''
              AND business.latitude IS NOT NULL
              AND business.longitude IS NOT NULL
        ), city_centers AS (
            SELECT
                state,
                city_key,
                MIN(city) AS city,
                MEDIAN(latitude) AS center_latitude,
                MEDIAN(longitude) AS center_longitude
            FROM business_city
            GROUP BY state, city_key
        ), city_distances AS (
            SELECT
                business.state,
                business.city_key,
                111.195 * SQRT(
                    POW(business.latitude - center.center_latitude, 2)
                    + POW(
                        (business.longitude - center.center_longitude)
                        * COS(RADIANS(center.center_latitude)),
                        2
                    )
                ) AS distance_km
            FROM business_city AS business
            INNER JOIN city_centers AS center USING (state, city_key)
        ), city_radii AS (
            SELECT
                state,
                city_key,
                QUANTILE_CONT(distance_km, 0.90) AS p90_radius_km
            FROM city_distances
            GROUP BY state, city_key
        ), annual AS (
            SELECT
                business.state,
                business.city_key,
                YEAR(CAST(review.date AS TIMESTAMP)) AS activity_year,
                COUNT(*) AS review_count,
                COUNT(DISTINCT review.user_id) AS active_reviewer_count,
                COUNT(DISTINCT review.business_id) AS active_business_count
            FROM read_parquet('{sql_path(reviews)}') AS review
            INNER JOIN business_city AS business USING (business_id)
            WHERE YEAR(CAST(review.date AS TIMESTAMP))
                  BETWEEN {first_year} AND {last_year}
            GROUP BY business.state, business.city_key, activity_year
        ), with_previous AS (
            SELECT
                *,
                LAG(activity_year) OVER (
                    PARTITION BY state, city_key ORDER BY activity_year
                ) AS previous_activity_year,
                LAG(review_count) OVER (
                    PARTITION BY state, city_key ORDER BY activity_year
                ) AS lag_review_count
            FROM annual
        )
        SELECT
            '{MODEL_VERSION}' AS model_version,
            annual.state,
            annual.city_key,
            center.city,
            CAST(annual.activity_year AS SMALLINT) AS activity_year,
            center.center_latitude,
            center.center_longitude,
            radius.p90_radius_km,
            CAST(annual.review_count AS BIGINT) AS review_count,
            CAST(annual.active_reviewer_count AS BIGINT)
                AS active_reviewer_count,
            CAST(annual.active_business_count AS BIGINT)
                AS active_business_count,
            CASE WHEN annual.previous_activity_year = annual.activity_year - 1
                THEN CAST(annual.lag_review_count AS BIGINT)
            END AS previous_year_review_count,
            CASE WHEN annual.previous_activity_year = annual.activity_year - 1
                THEN CAST(annual.review_count - annual.lag_review_count AS BIGINT)
            END AS yoy_review_change,
            CASE WHEN annual.previous_activity_year = annual.activity_year - 1
                       AND annual.lag_review_count > 0
                THEN (annual.review_count - annual.lag_review_count)
                     / annual.lag_review_count::DOUBLE
            END AS yoy_review_change_rate,
            annual.active_reviewer_count >= {MIN_ACTIVE_REVIEWERS}
                AND annual.review_count >= {MIN_ANNUAL_REVIEWS}
                AS minimum_sample_met,
            annual.activity_year = {last_year - 1} AS is_comparison_year,
            annual.activity_year = {last_year} AS is_selection_year,
            'all_restaurant_reviews_by_business_city' AS calculation_method
        FROM with_previous AS annual
        INNER JOIN city_centers AS center USING (state, city_key)
        INNER JOIN city_radii AS radius USING (state, city_key)
        ORDER BY annual.state, annual.city_key, annual.activity_year
        """
    ).fetchdf()
    connection.close()
    return frame


def build_newcomers(supply: pd.DataFrame) -> pd.DataFrame:
    history = pd.read_parquet(
        ROOT / "data" / "processed" / "reviewer_region_history_v04.parquet",
        columns=["model_version", "sample_id", "user_id", "selection_year", "state", "top_city"],
    )
    first_entry = history.sort_values(
        ["user_id", "selection_year", "sample_id"], kind="mergesort"
    ).drop_duplicates("user_id", keep="first")
    first_entry = first_entry.dropna(subset=["state", "top_city"]).copy()
    first_entry["city_key"] = normalize_city(first_entry["top_city"])

    city_names = (
        supply[["state", "city_key", "city"]]
        .drop_duplicates(["state", "city_key"])
    )
    newcomers = (
        first_entry.groupby(
            ["model_version", "selection_year", "state", "city_key"],
            as_index=False,
        )
        .agg(
            source_city=("top_city", "min"),
            new_power_reviewers=("user_id", "size"),
        )
        .merge(city_names, on=["state", "city_key"], how="left")
    )
    newcomers["city"] = newcomers["city"].fillna(newcomers["source_city"])
    return newcomers[
        [
            "model_version", "selection_year", "state", "city_key", "city",
            "new_power_reviewers",
        ]
    ].sort_values(["selection_year", "state", "city_key"], kind="mergesort")


def validate(supply: pd.DataFrame, newcomers: pd.DataFrame, last_year: int) -> None:
    supply_key = ["model_version", "state", "city_key", "activity_year"]
    newcomer_key = ["model_version", "selection_year", "state", "city_key"]
    if supply.duplicated(supply_key).any():
        raise ValueError("duplicate city review-supply key")
    if newcomers.duplicated(newcomer_key).any():
        raise ValueError("duplicate city newcomer key")
    if supply[supply_key].isna().any().any():
        raise ValueError("NULL city review-supply key")
    if newcomers[newcomer_key].isna().any().any():
        raise ValueError("NULL city newcomer key")
    selection = supply.loc[supply["activity_year"].eq(last_year)]
    eligible = selection.loc[selection["minimum_sample_met"]]
    if len(eligible) < 100:
        raise ValueError(f"unexpectedly few eligible cities: {len(eligible)}")
    if set(eligible["state"]) != set(selection["state"]):
        raise ValueError("one or more v04 states have no eligible city")


def main() -> None:
    config_path = ROOT / "configs" / "analysis_config_v04.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    first_year = int(config["cohort"]["minimum_selection_year"]) - 1
    last_year = int(config["cohort"]["test_selection_year"])

    supply = build_supply(first_year, last_year)
    newcomers = build_newcomers(supply)
    validate(supply, newcomers, last_year)

    output = ROOT / "data" / "processed"
    supply_path = output / "city_review_supply_v05.parquet"
    newcomer_path = output / "city_newcomers_v05.parquet"
    supply.to_parquet(supply_path, index=False)
    newcomers.to_parquet(newcomer_path, index=False)

    eligible = supply.loc[
        supply["activity_year"].eq(last_year) & supply["minimum_sample_met"]
    ]
    print(
        f"wrote {len(supply):,} city-year rows to {supply_path}; "
        f"{len(eligible):,} cities meet the {MIN_ACTIVE_REVIEWERS}-reviewer/"
        f"{MIN_ANNUAL_REVIEWS}-review minimum"
    )
    print(f"wrote {len(newcomers):,} city-entry rows to {newcomer_path}")


if __name__ == "__main__":
    main()
