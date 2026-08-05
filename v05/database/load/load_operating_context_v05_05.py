"""Atomically replace only the v05_05_dl unified operating-context rows."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_LOAD_DIR = PROJECT_ROOT / "database" / "load"
if str(DATABASE_LOAD_DIR) not in sys.path:
    sys.path.insert(0, str(DATABASE_LOAD_DIR))

from load_v04 import create_engine_from_env, database_name, sql_statements  # noqa: E402


MODEL_VERSION = "v05_05_dl"
PROCESSED = PROJECT_ROOT / "data" / "processed"
DDL_DIR = PROJECT_ROOT / "v05" / "database" / "ddl"


@dataclass(frozen=True)
class Artifact:
    table: str
    path: Path
    columns: tuple[str, ...]
    key: tuple[str, ...]


ARTIFACTS = (
    Artifact(
        "reviewer_region",
        PROCESSED / f"reviewer_region_{MODEL_VERSION}.parquet",
        ("model_version", "sample_id", "state", "top_city"),
        ("model_version", "sample_id"),
    ),
    Artifact(
        "reviewer_region_history",
        PROCESSED / f"reviewer_region_history_{MODEL_VERSION}.parquet",
        (
            "model_version", "sample_id", "user_id", "comparison_year",
            "selection_year", "baseline_review_count", "recent_review_count",
            "state", "top_city", "mapping_method",
        ),
        ("model_version", "sample_id"),
    ),
    Artifact(
        "reviewer_operating_entry",
        PROCESSED / f"reviewer_operating_entry_{MODEL_VERSION}.parquet",
        (
            "model_version", "sample_id", "user_id", "first_selection_year",
            "first_state", "first_city",
        ),
        ("model_version", "sample_id"),
    ),
    Artifact(
        "regional_newcomer",
        PROCESSED / f"regional_newcomers_{MODEL_VERSION}.parquet",
        ("model_version", "selection_year", "state", "new_power_reviewers"),
        ("model_version", "selection_year", "state"),
    ),
    Artifact(
        "regional_review_supply",
        PROCESSED / f"regional_review_supply_{MODEL_VERSION}.parquet",
        (
            "model_version", "state", "activity_year", "review_count",
            "active_reviewer_count", "active_business_count",
            "previous_year_review_count", "yoy_review_change",
            "yoy_review_change_rate", "is_comparison_year",
            "is_selection_year", "calculation_method",
        ),
        ("model_version", "state", "activity_year"),
    ),
    Artifact(
        "city_review_supply",
        PROCESSED / f"city_review_supply_{MODEL_VERSION}.parquet",
        (
            "model_version", "state", "city_key", "city", "activity_year",
            "center_latitude", "center_longitude", "p90_radius_km",
            "review_count", "active_reviewer_count", "active_business_count",
            "previous_year_review_count", "yoy_review_change",
            "yoy_review_change_rate", "minimum_sample_met",
            "is_comparison_year", "is_selection_year", "calculation_method",
        ),
        ("model_version", "state", "city_key", "activity_year"),
    ),
    Artifact(
        "city_newcomer",
        PROCESSED / f"city_newcomers_{MODEL_VERSION}.parquet",
        (
            "model_version", "selection_year", "state", "city_key", "city",
            "new_power_reviewers",
        ),
        ("model_version", "selection_year", "state", "city_key"),
    ),
    Artifact(
        "city_reviewer_migration",
        PROCESSED / f"city_reviewer_migration_{MODEL_VERSION}.parquet",
        (
            "model_version", "selection_year", "state", "city_key", "city",
            "outflow_count", "inflow_count", "net_migration",
        ),
        ("model_version", "selection_year", "state", "city_key"),
    ),
    Artifact(
        "business_review_supply",
        PROCESSED / f"business_review_supply_{MODEL_VERSION}.parquet",
        (
            "model_version", "business_id", "activity_year", "review_count",
            "previous_year_review_count", "yoy_review_change",
            "yoy_review_change_rate", "is_comparison_year",
            "is_selection_year", "calculation_method",
        ),
        ("model_version", "business_id", "activity_year"),
    ),
    Artifact(
        "reviewer_spatial_summary",
        PROCESSED / "spatial" / f"reviewer_spatial_summaries_{MODEL_VERSION}.parquet",
        (
            "model_version", "sample_id", "period_type", "activity_year",
            "center_latitude", "center_longitude", "spatial_business_count",
            "activity_review_count", "median_radius_km", "mean_radius_km",
            "p90_radius_km", "max_radius_km", "radius_available",
            "radius_change_km", "radius_change_rate", "center_shift_km",
        ),
        ("model_version", "sample_id", "period_type"),
    ),
    Artifact(
        "reviewer_restaurant_recommendation",
        PROCESSED / f"reviewer_restaurant_recommendations_{MODEL_VERSION}.parquet",
        (
            "model_version", "recommendation_version", "sample_id", "user_id",
            "selection_year", "business_id", "business_name", "city", "state",
            "distance_km", "matched_categories", "primary_category",
            "category_match_score", "stars", "review_count", "recommendation_rank",
            "radius_stage", "search_radius_km", "observed_p90_radius_km",
            "local_p90_radius_km", "travel_outlier_count", "activity_cluster_count",
            "primary_cluster_business_count", "reason",
        ),
        ("model_version", "sample_id", "recommendation_rank"),
    ),
    Artifact(
        "regional_weekday_pattern",
        PROCESSED / f"regional_weekday_pattern_{MODEL_VERSION}.parquet",
        (
            "model_version", "state", "activity_year", "iso_weekday",
            "review_count", "active_reviewer_count", "active_business_count",
            "calculation_method",
        ),
        ("model_version", "state", "activity_year", "iso_weekday"),
    ),
    Artifact(
        "city_weekday_pattern",
        PROCESSED / f"city_weekday_pattern_{MODEL_VERSION}.parquet",
        (
            "model_version", "state", "city_key", "city", "activity_year",
            "iso_weekday", "review_count", "active_reviewer_count",
            "active_business_count", "calculation_method",
        ),
        ("model_version", "state", "city_key", "activity_year", "iso_weekday"),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load the unified v05_05_dl operating context."
    )
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--confirm-replace", choices=[MODEL_VERSION], required=True)
    parser.add_argument("--chunk-size", type=int, default=1000)
    return parser.parse_args()


def apply_schema(connection) -> None:
    for filename in (
        "011_create_spatial_tables.sql", "012_create_spatial_views.sql",
        "013_create_v05_derived_tables.sql", "020_create_city_operating_tables.sql",
        "023_create_city_reviewer_migration.sql", "024_create_business_review_supply.sql",
        "028_create_regional_weekday_pattern.sql", "029_create_city_weekday_pattern.sql",
    ):
        for statement in sql_statements(DDL_DIR / filename):
            connection.exec_driver_sql(statement)

    existing = {
        row[0].lower()
        for row in connection.exec_driver_sql(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'reviewer_restaurant_recommendation'"
        )
    }
    for statement in sql_statements(DDL_DIR / "017_add_recommendation_context.sql"):
        match = re.search(r"ADD\s+COLUMN\s+([a-z0-9_]+)", statement, re.IGNORECASE)
        column = match.group(1).lower() if match else None
        if column and column not in existing:
            connection.exec_driver_sql(statement)
            existing.add(column)


def load_frames() -> dict[str, pd.DataFrame]:
    frames = {}
    for artifact in ARTIFACTS:
        if not artifact.path.is_file():
            raise FileNotFoundError(artifact.path)
        frame = pd.read_parquet(artifact.path)
        if artifact.table == "reviewer_region":
            frame.insert(0, "model_version", MODEL_VERSION)
        if artifact.table == "reviewer_region_history":
            frame = frame.loc[frame["selection_year"].eq(2018)].copy()
        missing = sorted(set(artifact.columns) - set(frame.columns))
        if missing:
            raise ValueError(f"{artifact.path.name}: missing columns {missing}")
        frame = frame.loc[:, artifact.columns].copy()
        if set(frame["model_version"].astype(str)) != {MODEL_VERSION}:
            raise ValueError(f"{artifact.path.name}: unexpected model_version")
        if frame[list(artifact.key)].isna().any().any():
            raise ValueError(f"{artifact.path.name}: NULL key")
        if frame.duplicated(list(artifact.key)).any():
            raise ValueError(f"{artifact.path.name}: duplicate key")
        frames[artifact.table] = frame.where(pd.notna(frame), None)
    return frames


def main() -> int:
    args = parse_args()
    frames = load_frames()
    engine = create_engine_from_env(PROJECT_ROOT)
    try:
        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"connected DB {actual_database!r} does not match "
                    f"confirmation {args.confirm_database!r}"
                )
            model_exists = int(connection.exec_driver_sql(
                "SELECT COUNT(*) FROM model_versions WHERE model_version=%s",
                (MODEL_VERSION,),
            ).scalar_one())
            cohort_count = int(connection.exec_driver_sql(
                "SELECT COUNT(*) FROM cohort_samples WHERE model_version=%s",
                (MODEL_VERSION,),
            ).scalar_one())
            if model_exists != 1 or cohort_count != 6_533:
                raise RuntimeError(
                    f"load v05_05_dl model/cohort first: model={model_exists}, "
                    f"cohort={cohort_count:,}"
                )
            apply_schema(connection)

            # Delete dependants before reviewer_region; v04 rows are untouched.
            for artifact in reversed(ARTIFACTS[1:]):
                connection.exec_driver_sql(
                    f"DELETE FROM {artifact.table} WHERE model_version=%s",
                    (MODEL_VERSION,),
                )
            connection.exec_driver_sql(
                "DELETE FROM reviewer_region WHERE model_version=%s",
                (MODEL_VERSION,),
            )

            for artifact in ARTIFACTS:
                frame = frames[artifact.table]
                frame.to_sql(
                    artifact.table, con=connection, if_exists="append", index=False,
                    chunksize=args.chunk_size, method="multi",
                )
                loaded = int(connection.exec_driver_sql(
                    f"SELECT COUNT(*) FROM {artifact.table} WHERE model_version=%s",
                    (MODEL_VERSION,),
                ).scalar_one())
                if loaded != len(frame):
                    raise RuntimeError(
                        f"{artifact.table}: loaded {loaded:,}, expected {len(frame):,}"
                    )
                print(f"loaded: {artifact.table} ({loaded:,} rows)")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
