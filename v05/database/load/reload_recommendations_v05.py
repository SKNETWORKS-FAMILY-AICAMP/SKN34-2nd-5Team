"""Replace only v04 operational recommendation rows with the v05 derivation."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_LOAD_DIR = PROJECT_ROOT / "database" / "load"
if str(DATABASE_LOAD_DIR) not in sys.path:
    sys.path.insert(0, str(DATABASE_LOAD_DIR))

from load_v04 import create_engine_from_env, database_name, sql_statements  # noqa: E402


MODEL_VERSION = "v04"
RECOMMENDATION_VERSION = "v05_primary_cluster_radius"
PARQUET_PATH = (
    PROJECT_ROOT / "data" / "processed" / "reviewer_restaurant_recommendations_v05.parquet"
)
DDL_PATH = PROJECT_ROOT / "v05" / "database" / "ddl" / "017_add_recommendation_context.sql"
COLUMNS = (
    "model_version", "recommendation_version", "sample_id", "user_id",
    "selection_year", "business_id", "business_name", "city", "state",
    "distance_km", "matched_categories", "primary_category",
    "category_match_score", "stars", "review_count", "recommendation_rank",
    "radius_stage", "search_radius_km", "observed_p90_radius_km",
    "local_p90_radius_km", "travel_outlier_count", "activity_cluster_count",
    "primary_cluster_business_count", "reason",
)


def apply_missing_columns(connection) -> None:
    existing = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'reviewer_restaurant_recommendation'"
        )
    }
    for statement in sql_statements(DDL_PATH):
        match = re.search(r"ADD\s+COLUMN\s+([a-z0-9_]+)", statement, re.IGNORECASE)
        target = match.group(1).lower() if match else None
        if target and target not in existing:
            connection.exec_driver_sql(statement)
            existing.add(target)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--confirm-replace", choices=[MODEL_VERSION], required=True)
    parser.add_argument("--chunk-size", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frame = pd.read_parquet(PARQUET_PATH)
    missing = sorted(set(COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    frame = frame.loc[:, COLUMNS].copy()
    if set(frame["model_version"]) != {MODEL_VERSION}:
        raise ValueError("unexpected model version")
    if set(frame["recommendation_version"]) != {RECOMMENDATION_VERSION}:
        raise ValueError("unexpected recommendation version")
    if frame.duplicated(["model_version", "sample_id", "recommendation_rank"]).any():
        raise ValueError("duplicate recommendation rank")

    engine = create_engine_from_env(PROJECT_ROOT)
    try:
        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"connected DB {actual_database!r} does not match {args.confirm_database!r}"
                )
            apply_missing_columns(connection)
            existing = int(
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM reviewer_restaurant_recommendation WHERE model_version=%s",
                    (MODEL_VERSION,),
                ).scalar_one()
            )
            connection.exec_driver_sql(
                "DELETE FROM reviewer_restaurant_recommendation WHERE model_version=%s",
                (MODEL_VERSION,),
            )
            frame.where(pd.notna(frame), None).to_sql(
                "reviewer_restaurant_recommendation",
                con=connection,
                if_exists="append",
                index=False,
                chunksize=args.chunk_size,
                method="multi",
            )
            loaded = int(
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM reviewer_restaurant_recommendation WHERE model_version=%s",
                    (MODEL_VERSION,),
                ).scalar_one()
            )
            if loaded != len(frame):
                raise RuntimeError(f"loaded {loaded:,}, expected {len(frame):,}")
            print(f"replaced {existing:,} rows with {loaded:,} {RECOMMENDATION_VERSION} rows")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
