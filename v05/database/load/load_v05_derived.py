"""Load v05 G-1/G-2/G-4 Parquet artifacts into the existing yelp_data DB.

This script is intentionally manual. It creates only the v05 tables, refuses
to append when the selected model version already has rows, and loads all four
artifacts in one transaction.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_LOAD_DIR = PROJECT_ROOT / "database" / "load"
if str(DATABASE_LOAD_DIR) not in sys.path:
    sys.path.insert(0, str(DATABASE_LOAD_DIR))

from load_v04 import create_engine_from_env, database_name, sql_statements  # noqa: E402


MODEL_VERSION = "v04"
DDL_PATH = PROJECT_ROOT / "v05" / "database" / "ddl" / "013_create_v05_derived_tables.sql"


@dataclass(frozen=True)
class Artifact:
    table: str
    filename: str
    columns: tuple[str, ...]
    key: tuple[str, ...]


ARTIFACTS = (
    Artifact(
        "reviewer_restaurant_recommendation",
        "reviewer_restaurant_recommendations_v04.parquet",
        (
            "model_version", "sample_id", "user_id", "selection_year",
            "business_id", "business_name", "city", "state", "distance_km",
            "matched_categories", "primary_category", "category_match_score",
            "stars", "review_count", "recommendation_rank", "radius_stage",
            "search_radius_km", "reason",
        ),
        ("model_version", "sample_id", "recommendation_rank"),
    ),
    Artifact(
        "reviewer_region_history",
        "reviewer_region_history_v04.parquet",
        (
            "model_version", "sample_id", "user_id", "comparison_year",
            "selection_year", "baseline_review_count", "recent_review_count",
            "state", "top_city", "mapping_method",
        ),
        ("model_version", "sample_id"),
    ),
    Artifact(
        "regional_newcomer",
        "regional_newcomers_v04.parquet",
        ("model_version", "selection_year", "state", "new_power_reviewers"),
        ("model_version", "selection_year", "state"),
    ),
    Artifact(
        "regional_review_supply",
        "regional_review_supply_v04.parquet",
        (
            "model_version", "state", "activity_year", "review_count",
            "active_reviewer_count", "active_business_count",
            "previous_year_review_count", "yoy_review_change",
            "yoy_review_change_rate", "is_comparison_year",
            "is_selection_year", "calculation_method",
        ),
        ("model_version", "state", "activity_year"),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load reviewed v05 derived Parquet artifacts into yelp_data."
    )
    parser.add_argument(
        "--confirm-database",
        required=True,
        help="Safety check: enter the exact target database name.",
    )
    parser.add_argument("--chunk-size", type=int, default=1000)
    return parser.parse_args()


def apply_schema(connection) -> None:
    if not DDL_PATH.is_file():
        raise FileNotFoundError(DDL_PATH)
    for statement in sql_statements(DDL_PATH):
        connection.exec_driver_sql(statement)
    print(f"schema applied: {DDL_PATH.name}")


def load_frames() -> dict[str, pd.DataFrame]:
    processed = PROJECT_ROOT / "data" / "processed"
    frames: dict[str, pd.DataFrame] = {}
    for artifact in ARTIFACTS:
        path = processed / artifact.filename
        if not path.is_file():
            raise FileNotFoundError(path)
        frame = pd.read_parquet(path)
        missing = sorted(set(artifact.columns) - set(frame.columns))
        if missing:
            raise ValueError(f"{artifact.filename}: missing columns {missing}")
        frame = frame.loc[:, artifact.columns].copy()
        if frame[list(artifact.key)].isna().any().any():
            raise ValueError(f"{artifact.filename}: NULL key")
        if frame.duplicated(list(artifact.key)).any():
            raise ValueError(f"{artifact.filename}: duplicate key")
        versions = set(frame["model_version"].astype(str))
        if versions != {MODEL_VERSION}:
            raise ValueError(f"{artifact.filename}: model versions {versions}")
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
            apply_schema(connection)
            for artifact in ARTIFACTS:
                existing = int(
                    connection.exec_driver_sql(
                        f"SELECT COUNT(*) FROM {artifact.table} WHERE model_version = %s",
                        (MODEL_VERSION,),
                    ).scalar_one()
                )
                if existing:
                    raise RuntimeError(
                        f"{artifact.table} already has {existing:,} rows for "
                        f"{MODEL_VERSION}; no data was appended"
                    )
            for artifact in ARTIFACTS:
                frame = frames[artifact.table]
                frame.to_sql(
                    artifact.table,
                    con=connection,
                    if_exists="append",
                    index=False,
                    chunksize=args.chunk_size,
                    method="multi",
                )
                loaded = int(
                    connection.exec_driver_sql(
                        f"SELECT COUNT(*) FROM {artifact.table} WHERE model_version = %s",
                        (MODEL_VERSION,),
                    ).scalar_one()
                )
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
