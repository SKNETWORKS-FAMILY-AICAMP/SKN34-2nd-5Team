"""Build one v05_05_dl operating context from the approved culinary scope.

The prediction rows are not recalculated here.  This pipeline aligns the
geographic and content context shown around those predictions to the same
Restaurants + selected culinary-business universe documented by DEC-007.
Legacy v04 artifacts are inputs only where their underlying calculation
already used that universe (spatial summaries and v05 recommendations).
"""
from __future__ import annotations

from pathlib import Path
import sys

import duckdb
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v04.derived_reviewer_activity import (  # noqa: E402
    derive_reviewer_region,
    reviews_in_feature_window,
)
from v05.pipeline.derive_city_reviewer_migration_v04 import (  # noqa: E402
    primary_cities,
)


MODEL_VERSION = "v05_05_dl"
COMPARISON_YEAR = 2017
SELECTION_YEAR = 2018
MIN_ACTIVE_REVIEWERS = 30
MIN_ANNUAL_REVIEWS = 100
CALCULATION_METHOD = "restaurant_and_culinary_reviews"

INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
SPATIAL = PROCESSED / "spatial"


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def output_path(name: str, *, spatial: bool = False) -> Path:
    directory = SPATIAL if spatial else PROCESSED
    return directory / f"{name}_{MODEL_VERSION}.parquet"


def source_paths() -> dict[str, Path]:
    return {
        "restaurant_reviews": INTERIM / "restaurant_reviews.parquet",
        "culinary_reviews": INTERIM / "additional_culinary_reviews_v02.parquet",
        "restaurant_businesses": INTERIM / "restaurant_businesses.parquet",
        "culinary_businesses": INTERIM / "additional_culinary_businesses_v02.parquet",
        "profiles": INTERIM / "rolling" / "culinary_rolling_cohort_master_v04.parquet",
        "spatial_summary": SPATIAL / "reviewer_spatial_summaries_v04.parquet",
        "spatial_activity": SPATIAL / "reviewer_activity_locations_v04.parquet",
        "business_locations": SPATIAL / "business_locations_v04.parquet",
        "recommendations": PROCESSED / "reviewer_restaurant_recommendations_v05.parquet",
        "business_supply": PROCESSED / "business_review_supply_v04.parquet",
    }


def validate_sources(paths: dict[str, Path]) -> None:
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing source artifacts: {missing}")


def read_profiles(path: Path) -> pd.DataFrame:
    return pd.read_parquet(
        path,
        columns=[
            "sample_id", "user_id", "comparison_year", "selection_year",
            "baseline_review_count", "recent_review_count",
        ],
    )


def read_reviews(paths: dict[str, Path]) -> pd.DataFrame:
    columns = ["user_id", "business_id", "date"]
    return pd.concat(
        [
            pd.read_parquet(paths["restaurant_reviews"], columns=columns),
            pd.read_parquet(paths["culinary_reviews"], columns=columns),
        ],
        ignore_index=True,
    )


def read_businesses(paths: dict[str, Path]) -> pd.DataFrame:
    columns = ["business_id", "city", "state"]
    frame = pd.concat(
        [
            pd.read_parquet(paths["restaurant_businesses"], columns=columns),
            pd.read_parquet(paths["culinary_businesses"], columns=columns),
        ],
        ignore_index=True,
    )
    if frame["business_id"].duplicated().any():
        raise ValueError("combined culinary businesses contain duplicate business_id")
    return frame


def build_region_context(
    profiles: pd.DataFrame,
    reviews: pd.DataFrame,
    businesses: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    window = reviews_in_feature_window(profiles, reviews)
    # Derive one cohort year at a time.  The published helper intentionally
    # preserves its historical equal-count tie behavior, so mixing all cohort
    # years in a single global sort can make a test-year tie depend on rows from
    # other years.  Per-year derivation keeps the result stable and auditable.
    region_parts = []
    for selection_year, year_profiles in profiles.groupby("selection_year", sort=True):
        sample_ids = set(year_profiles["sample_id"].astype(str))
        year_window = window.loc[window["sample_id"].astype(str).isin(sample_ids)]
        region_parts.append(derive_reviewer_region(year_window, businesses))
    region = pd.concat(region_parts, ignore_index=True)
    history = profiles.merge(region, on=["sample_id", "user_id"], how="inner")
    history.insert(0, "model_version", MODEL_VERSION)
    history["mapping_method"] = "combined_culinary_feature_window"
    history = history[
        [
            "model_version", "sample_id", "user_id", "comparison_year",
            "selection_year", "baseline_review_count", "recent_review_count",
            "state", "top_city", "mapping_method",
        ]
    ].sort_values(["selection_year", "sample_id"], kind="mergesort")

    reviewer_region = history.loc[
        history["selection_year"].eq(SELECTION_YEAR),
        ["sample_id", "user_id", "state", "top_city"],
    ].sort_values("sample_id", kind="mergesort")

    first_entry = history.sort_values(
        ["user_id", "selection_year", "sample_id"], kind="mergesort"
    ).drop_duplicates("user_id", keep="first")
    newcomers = (
        first_entry.groupby(["model_version", "selection_year", "state"], as_index=False)
        .size()
        .rename(columns={"size": "new_power_reviewers"})
        .sort_values(["selection_year", "state"], kind="mergesort")
    )
    return reviewer_region, history, newcomers


def build_operating_entry(
    reviewer_region: pd.DataFrame, history: pd.DataFrame
) -> pd.DataFrame:
    first = history.sort_values(
        ["user_id", "selection_year", "sample_id"], kind="mergesort"
    ).drop_duplicates("user_id", keep="first")
    first = first.rename(
        columns={
            "selection_year": "first_selection_year",
            "state": "first_state",
            "top_city": "first_city",
        }
    )
    current = reviewer_region[["sample_id", "user_id"]].merge(
        first[["user_id", "first_selection_year", "first_state", "first_city"]],
        on="user_id", how="left", validate="one_to_one",
    )
    current.insert(0, "model_version", MODEL_VERSION)
    return current.sort_values("sample_id", kind="mergesort")


def register_unified_views(connection: duckdb.DuckDBPyConnection, paths: dict[str, Path]) -> None:
    connection.execute(
        f"""
        CREATE TEMP VIEW unified_reviews AS
        SELECT user_id, business_id, CAST(date AS TIMESTAMP) AS review_date
        FROM read_parquet('{sql_path(paths['restaurant_reviews'])}')
        UNION ALL
        SELECT user_id, business_id, CAST(date AS TIMESTAMP) AS review_date
        FROM read_parquet('{sql_path(paths['culinary_reviews'])}');

        CREATE TEMP VIEW unified_businesses AS
        SELECT business_id, city, state, latitude, longitude
        FROM read_parquet('{sql_path(paths['restaurant_businesses'])}')
        UNION ALL
        SELECT business_id, city, state, latitude, longitude
        FROM read_parquet('{sql_path(paths['culinary_businesses'])}');
        """
    )


def build_regional_supply(
    connection: duckdb.DuckDBPyConnection,
    regions: list[str],
    first_year: int,
) -> pd.DataFrame:
    region_sql = ", ".join(f"'{state.replace(chr(39), chr(39) * 2)}'" for state in regions)
    return connection.execute(
        f"""
        WITH annual AS (
            SELECT business.state,
                   YEAR(review.review_date) AS activity_year,
                   COUNT(*) AS review_count,
                   COUNT(DISTINCT review.user_id) AS active_reviewer_count,
                   COUNT(DISTINCT review.business_id) AS active_business_count
            FROM unified_reviews AS review
            INNER JOIN unified_businesses AS business USING (business_id)
            WHERE business.state IN ({region_sql})
              AND YEAR(review.review_date) BETWEEN {first_year} AND {SELECTION_YEAR}
            GROUP BY business.state, activity_year
        ), lagged AS (
            SELECT *, LAG(review_count) OVER (
                PARTITION BY state ORDER BY activity_year
            ) AS previous_year_review_count
            FROM annual
        )
        SELECT '{MODEL_VERSION}' AS model_version, state,
               CAST(activity_year AS SMALLINT) AS activity_year,
               CAST(review_count AS BIGINT) AS review_count,
               CAST(active_reviewer_count AS BIGINT) AS active_reviewer_count,
               CAST(active_business_count AS BIGINT) AS active_business_count,
               CAST(previous_year_review_count AS BIGINT) AS previous_year_review_count,
               CAST(review_count - previous_year_review_count AS BIGINT) AS yoy_review_change,
               CASE WHEN previous_year_review_count > 0
                    THEN (review_count - previous_year_review_count)
                         / previous_year_review_count::DOUBLE END AS yoy_review_change_rate,
               activity_year = {COMPARISON_YEAR} AS is_comparison_year,
               activity_year = {SELECTION_YEAR} AS is_selection_year,
               '{CALCULATION_METHOD}_by_state' AS calculation_method
        FROM lagged ORDER BY state, activity_year
        """
    ).fetchdf()


def build_city_supply(
    connection: duckdb.DuckDBPyConnection,
    regions: list[str],
    first_year: int,
) -> pd.DataFrame:
    region_sql = ", ".join(f"'{state.replace(chr(39), chr(39) * 2)}'" for state in regions)
    return connection.execute(
        f"""
        WITH business_city AS (
            SELECT business_id, state, LOWER(TRIM(city)) AS city_key,
                   TRIM(city) AS city, latitude::DOUBLE AS latitude,
                   longitude::DOUBLE AS longitude
            FROM unified_businesses
            WHERE state IN ({region_sql}) AND city IS NOT NULL AND TRIM(city) <> ''
              AND latitude IS NOT NULL AND longitude IS NOT NULL
        ), centers AS (
            SELECT state, city_key, MIN(city) AS city,
                   MEDIAN(latitude) AS center_latitude,
                   MEDIAN(longitude) AS center_longitude
            FROM business_city GROUP BY state, city_key
        ), radii AS (
            SELECT business.state, business.city_key,
                   QUANTILE_CONT(111.195 * SQRT(
                       POW(business.latitude - center.center_latitude, 2)
                       + POW((business.longitude - center.center_longitude)
                             * COS(RADIANS(center.center_latitude)), 2)
                   ), 0.90) AS p90_radius_km
            FROM business_city AS business
            INNER JOIN centers AS center USING (state, city_key)
            GROUP BY business.state, business.city_key
        ), annual AS (
            SELECT business.state, business.city_key,
                   YEAR(review.review_date) AS activity_year,
                   COUNT(*) AS review_count,
                   COUNT(DISTINCT review.user_id) AS active_reviewer_count,
                   COUNT(DISTINCT review.business_id) AS active_business_count
            FROM unified_reviews AS review
            INNER JOIN business_city AS business USING (business_id)
            WHERE YEAR(review.review_date) BETWEEN {first_year} AND {SELECTION_YEAR}
            GROUP BY business.state, business.city_key, activity_year
        ), lagged AS (
            SELECT *,
                   LAG(activity_year) OVER (
                       PARTITION BY state, city_key ORDER BY activity_year
                   ) AS previous_activity_year,
                   LAG(review_count) OVER (
                       PARTITION BY state, city_key ORDER BY activity_year
                   ) AS lag_review_count
            FROM annual
        )
        SELECT '{MODEL_VERSION}' AS model_version, annual.state, annual.city_key,
               center.city, annual.activity_year::SMALLINT AS activity_year,
               center.center_latitude, center.center_longitude, radius.p90_radius_km,
               annual.review_count::BIGINT AS review_count,
               annual.active_reviewer_count::BIGINT AS active_reviewer_count,
               annual.active_business_count::BIGINT AS active_business_count,
               CASE WHEN previous_activity_year = activity_year - 1
                    THEN lag_review_count::BIGINT END AS previous_year_review_count,
               CASE WHEN previous_activity_year = activity_year - 1
                    THEN (review_count - lag_review_count)::BIGINT END AS yoy_review_change,
               CASE WHEN previous_activity_year = activity_year - 1 AND lag_review_count > 0
                    THEN (review_count - lag_review_count) / lag_review_count::DOUBLE
                    END AS yoy_review_change_rate,
               active_reviewer_count >= {MIN_ACTIVE_REVIEWERS}
                   AND review_count >= {MIN_ANNUAL_REVIEWS} AS minimum_sample_met,
               activity_year = {COMPARISON_YEAR} AS is_comparison_year,
               activity_year = {SELECTION_YEAR} AS is_selection_year,
               '{CALCULATION_METHOD}_by_city' AS calculation_method
        FROM lagged AS annual
        INNER JOIN centers AS center USING (state, city_key)
        INNER JOIN radii AS radius USING (state, city_key)
        ORDER BY annual.state, annual.city_key, annual.activity_year
        """
    ).fetchdf()


def normalize_city(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower()


def build_city_newcomers(history: pd.DataFrame, city_supply: pd.DataFrame) -> pd.DataFrame:
    first = history.sort_values(
        ["user_id", "selection_year", "sample_id"], kind="mergesort"
    ).drop_duplicates("user_id", keep="first")
    first = first.dropna(subset=["state", "top_city"]).copy()
    first["city_key"] = normalize_city(first["top_city"])
    names = city_supply[["state", "city_key", "city"]].drop_duplicates(
        ["state", "city_key"]
    )
    result = (
        first.groupby(["model_version", "selection_year", "state", "city_key"], as_index=False)
        .agg(source_city=("top_city", "min"), new_power_reviewers=("user_id", "size"))
        .merge(names, on=["state", "city_key"], how="left")
    )
    result["city"] = result["city"].fillna(result["source_city"])
    return result[
        ["model_version", "selection_year", "state", "city_key", "city", "new_power_reviewers"]
    ].sort_values(["selection_year", "state", "city_key"], kind="mergesort")


def build_city_migration(paths: dict[str, Path]) -> pd.DataFrame:
    activity = pd.read_parquet(
        paths["spatial_activity"],
        columns=["sample_id", "period_type", "business_id", "review_count"],
    )
    businesses = pd.read_parquet(
        paths["business_locations"], columns=["business_id", "state", "city"]
    ).dropna(subset=["state", "city"]).copy()
    businesses["city"] = businesses["city"].astype("string").str.strip()
    businesses["city_key"] = normalize_city(businesses["city"])
    primary = primary_cities(activity, businesses)
    wide = primary.pivot(
        index="sample_id", columns="period_type", values=["state", "city_key", "city"]
    )
    wide.columns = [f"{value}_{period}" for value, period in wide.columns]
    required = [
        "state_comparison", "city_key_comparison", "city_comparison",
        "state_selection", "city_key_selection", "city_selection",
    ]
    wide = wide.dropna(subset=required)
    movers = wide.loc[
        wide["state_comparison"].ne(wide["state_selection"])
        | wide["city_key_comparison"].ne(wide["city_key_selection"])
    ]
    outflow = (
        movers.groupby(["state_comparison", "city_key_comparison"], as_index=False)
        .agg(outflow_count=("city_key_comparison", "size"), city_out=("city_comparison", "min"))
        .rename(columns={"state_comparison": "state", "city_key_comparison": "city_key"})
    )
    inflow = (
        movers.groupby(["state_selection", "city_key_selection"], as_index=False)
        .agg(inflow_count=("city_key_selection", "size"), city_in=("city_selection", "min"))
        .rename(columns={"state_selection": "state", "city_key_selection": "city_key"})
    )
    result = outflow.merge(inflow, on=["state", "city_key"], how="outer")
    result["outflow_count"] = result["outflow_count"].fillna(0).astype(int)
    result["inflow_count"] = result["inflow_count"].fillna(0).astype(int)
    result["city"] = result["city_out"].fillna(result["city_in"])
    result["net_migration"] = result["inflow_count"] - result["outflow_count"]
    result.insert(0, "model_version", MODEL_VERSION)
    result.insert(1, "selection_year", SELECTION_YEAR)
    return result[
        [
            "model_version", "selection_year", "state", "city_key", "city",
            "outflow_count", "inflow_count", "net_migration",
        ]
    ].sort_values(["state", "city_key"], kind="mergesort")


def build_regional_weekday_pattern(
    connection: duckdb.DuckDBPyConnection, regions: list[str]
) -> pd.DataFrame:
    region_sql = ", ".join(f"'{state.replace(chr(39), chr(39) * 2)}'" for state in regions)
    return connection.execute(
        f"""
        SELECT '{MODEL_VERSION}' AS model_version, business.state,
               {SELECTION_YEAR}::SMALLINT AS activity_year,
               ISODOW(review.review_date)::TINYINT AS iso_weekday,
               COUNT(*)::BIGINT AS review_count,
               COUNT(DISTINCT review.user_id)::BIGINT AS active_reviewer_count,
               COUNT(DISTINCT review.business_id)::BIGINT AS active_business_count,
               '{CALCULATION_METHOD}_by_iso_weekday' AS calculation_method
        FROM unified_reviews AS review
        INNER JOIN unified_businesses AS business USING (business_id)
        WHERE business.state IN ({region_sql})
          AND YEAR(review.review_date) = {SELECTION_YEAR}
        GROUP BY business.state, iso_weekday
        ORDER BY business.state, iso_weekday
        """
    ).fetchdf()


def build_city_weekday_pattern(
    connection: duckdb.DuckDBPyConnection, regions: list[str]
) -> pd.DataFrame:
    region_sql = ", ".join(f"'{state.replace(chr(39), chr(39) * 2)}'" for state in regions)
    return connection.execute(
        f"""
        SELECT '{MODEL_VERSION}' AS model_version, business.state,
               LOWER(TRIM(business.city)) AS city_key,
               MIN(TRIM(business.city)) AS city,
               {SELECTION_YEAR}::SMALLINT AS activity_year,
               ISODOW(review.review_date)::TINYINT AS iso_weekday,
               COUNT(*)::BIGINT AS review_count,
               COUNT(DISTINCT review.user_id)::BIGINT AS active_reviewer_count,
               COUNT(DISTINCT review.business_id)::BIGINT AS active_business_count,
               '{CALCULATION_METHOD}_by_city_iso_weekday' AS calculation_method
        FROM unified_reviews AS review
        INNER JOIN unified_businesses AS business USING (business_id)
        WHERE business.state IN ({region_sql})
          AND business.city IS NOT NULL AND TRIM(business.city) <> ''
          AND business.latitude IS NOT NULL AND business.longitude IS NOT NULL
          AND YEAR(review.review_date) = {SELECTION_YEAR}
        GROUP BY business.state, city_key, iso_weekday
        ORDER BY business.state, city_key, iso_weekday
        """
    ).fetchdf()


def reversion(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    frame["model_version"] = MODEL_VERSION
    return frame


def validate_outputs(outputs: dict[str, pd.DataFrame]) -> None:
    keys = {
        "reviewer_region": ["sample_id"],
        "reviewer_region_history": ["model_version", "sample_id"],
        "reviewer_operating_entry": ["model_version", "sample_id"],
        "regional_newcomers": ["model_version", "selection_year", "state"],
        "regional_review_supply": ["model_version", "state", "activity_year"],
        "city_review_supply": ["model_version", "state", "city_key", "activity_year"],
        "city_newcomers": ["model_version", "selection_year", "state", "city_key"],
        "city_reviewer_migration": ["model_version", "selection_year", "state", "city_key"],
        "business_review_supply": ["model_version", "business_id", "activity_year"],
        "reviewer_spatial_summaries": ["model_version", "sample_id", "period_type"],
        "reviewer_restaurant_recommendations": ["model_version", "sample_id", "recommendation_rank"],
        "regional_weekday_pattern": ["model_version", "state", "activity_year", "iso_weekday"],
        "city_weekday_pattern": ["model_version", "state", "city_key", "activity_year", "iso_weekday"],
    }
    for name, frame in outputs.items():
        key = keys[name]
        if frame.empty:
            raise ValueError(f"{name}: empty artifact")
        if frame[key].isna().any().any():
            raise ValueError(f"{name}: NULL key")
        if frame.duplicated(key).any():
            raise ValueError(f"{name}: duplicate key")
        if "model_version" in frame and set(frame["model_version"].astype(str)) != {MODEL_VERSION}:
            raise ValueError(f"{name}: unexpected model version")
    if len(outputs["reviewer_region"]) != 6_533:
        raise ValueError("reviewer_region must cover all 6,533 test samples")
    weekday = outputs["regional_weekday_pattern"]
    counts = weekday.groupby("state")["iso_weekday"].nunique()
    if not counts.eq(7).all():
        raise ValueError("every region must have all seven weekdays")
    city_weekday = outputs["city_weekday_pattern"]
    city_supply_keys = set(
        outputs["city_review_supply"].loc[
            outputs["city_review_supply"]["activity_year"].eq(SELECTION_YEAR),
            ["state", "city_key"],
        ].itertuples(index=False, name=None)
    )
    if not set(city_weekday[["state", "city_key"]].itertuples(index=False, name=None)).issubset(city_supply_keys):
        raise ValueError("city weekday rows must belong to selection-year city supply")


def main() -> None:
    paths = source_paths()
    validate_sources(paths)
    config_path = ROOT / "configs" / "analysis_config_v04.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    first_year = int(config["cohort"]["minimum_selection_year"]) - 1

    profiles = read_profiles(paths["profiles"])
    reviews = read_reviews(paths)
    businesses = read_businesses(paths)
    reviewer_region, history, regional_newcomers = build_region_context(
        profiles, reviews, businesses
    )
    regions = sorted(reviewer_region["state"].dropna().astype(str).unique())
    if len(regions) != 14:
        raise ValueError(f"expected 14 operating regions, found {len(regions)}: {regions}")

    connection = duckdb.connect()
    try:
        register_unified_views(connection, paths)
        regional_supply = build_regional_supply(connection, regions, first_year)
        city_supply = build_city_supply(connection, regions, first_year)
        weekday = build_regional_weekday_pattern(connection, regions)
        city_weekday = build_city_weekday_pattern(connection, regions)
    finally:
        connection.close()

    outputs = {
        "reviewer_region": reviewer_region,
        "reviewer_region_history": history,
        "reviewer_operating_entry": build_operating_entry(reviewer_region, history),
        "regional_newcomers": regional_newcomers,
        "regional_review_supply": regional_supply,
        "city_review_supply": city_supply,
        "city_newcomers": build_city_newcomers(history, city_supply),
        "city_reviewer_migration": build_city_migration(paths),
        "business_review_supply": reversion(paths["business_supply"]),
        "reviewer_spatial_summaries": reversion(paths["spatial_summary"]),
        "reviewer_restaurant_recommendations": reversion(paths["recommendations"]),
        "regional_weekday_pattern": weekday,
        "city_weekday_pattern": city_weekday,
    }
    validate_outputs(outputs)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    SPATIAL.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        destination = output_path(
            name, spatial=name == "reviewer_spatial_summaries"
        )
        frame.to_parquet(destination, index=False)
        print(f"wrote {len(frame):,} rows: {destination}")

    old_region = pd.read_parquet(
        PROCESSED / "reviewer_region_v04.parquet",
        columns=["sample_id", "state", "top_city"],
    )
    comparison = old_region.merge(
        reviewer_region[["sample_id", "state", "top_city"]],
        on="sample_id", suffixes=("_v04", "_unified"), validate="one_to_one",
    )
    changed_states = comparison["state_v04"].fillna("").ne(
        comparison["state_unified"].fillna("")
    ).sum()
    changed_cities = comparison["top_city_v04"].fillna("").ne(
        comparison["top_city_unified"].fillna("")
    ).sum()
    print(f"context changes vs v04: state={changed_states:,}, city={changed_cities:,}")


if __name__ == "__main__":
    main()
