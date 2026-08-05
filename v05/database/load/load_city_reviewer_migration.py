"""Load reviewed v05 city reviewer-migration artifact into yelp_data.

The loader applies only v05/database/ddl/023_create_city_reviewer_migration.sql,
refuses to append when v04 rows already exist.
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
DDL_PATH = (
    PROJECT_ROOT
    / "v05"
    / "database"
    / "ddl"
    / "023_create_city_reviewer_migration.sql"
)


@dataclass(frozen=True)
class Artifact:
    table: str
    filename: str
    columns: tuple[str, ...]
    key: tuple[str, ...]


ARTIFACT = Artifact(
    "city_reviewer_migration",
    "city_reviewer_migration_v04.parquet",
    (
        "model_version", "selection_year", "state", "city_key", "city",
        "outflow_count", "inflow_count", "net_migration",
    ),
    ("model_version", "selection_year", "state", "city_key"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load the reviewed v05 city reviewer-migration Parquet artifact."
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


def load_frame() -> pd.DataFrame:
    processed = PROJECT_ROOT / "data" / "processed"
    path = processed / ARTIFACT.filename
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_parquet(path)
    missing = sorted(set(ARTIFACT.columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{ARTIFACT.filename}: missing columns {missing}")
    frame = frame.loc[:, ARTIFACT.columns].copy()
    if frame[list(ARTIFACT.key)].isna().any().any():
        raise ValueError(f"{ARTIFACT.filename}: NULL key")
    if frame.duplicated(list(ARTIFACT.key)).any():
        raise ValueError(f"{ARTIFACT.filename}: duplicate key")
    if set(frame["model_version"].astype(str)) != {MODEL_VERSION}:
        raise ValueError(f"{ARTIFACT.filename}: unexpected model version")
    return frame.where(pd.notna(frame), None)


def main() -> int:
    args = parse_args()
    frame = load_frame()
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
            existing = int(
                connection.exec_driver_sql(
                    f"SELECT COUNT(*) FROM {ARTIFACT.table} "
                    "WHERE model_version = %s",
                    (MODEL_VERSION,),
                ).scalar_one()
            )
            if existing:
                raise RuntimeError(
                    f"{ARTIFACT.table} already has {existing:,} rows for "
                    f"{MODEL_VERSION}; no data was appended"
                )
            frame.to_sql(
                ARTIFACT.table,
                con=connection,
                if_exists="append",
                index=False,
                chunksize=args.chunk_size,
                method="multi",
            )
            loaded = int(
                connection.exec_driver_sql(
                    f"SELECT COUNT(*) FROM {ARTIFACT.table} "
                    "WHERE model_version = %s",
                    (MODEL_VERSION,),
                ).scalar_one()
            )
            if loaded != len(frame):
                raise RuntimeError(
                    f"{ARTIFACT.table}: loaded {loaded:,}, expected {len(frame):,}"
                )
            print(f"loaded: {ARTIFACT.table} ({loaded:,} rows)")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
