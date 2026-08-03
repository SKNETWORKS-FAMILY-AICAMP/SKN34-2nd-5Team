"""Load the recommendation-scoped Yelp photo manifest into yelp_data."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_LOAD_DIR = PROJECT_ROOT / "database" / "load"
if str(DATABASE_LOAD_DIR) not in sys.path:
    sys.path.insert(0, str(DATABASE_LOAD_DIR))

from load_v04 import create_engine_from_env, database_name, sql_statements  # noqa: E402


PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "business_photos_v01.parquet"
DDL_PATH = PROJECT_ROOT / "v05" / "database" / "ddl" / "018_create_business_photos.sql"
COLUMNS = ("photo_id", "business_id", "label", "caption", "display_rank", "source_type")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--chunk-size", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frame = pd.read_parquet(PARQUET_PATH)
    missing = sorted(set(COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    frame = frame.loc[:, COLUMNS].copy()
    if frame["photo_id"].duplicated().any():
        raise ValueError("duplicate photo_id")
    if frame.duplicated(["business_id", "display_rank"]).any():
        raise ValueError("duplicate business display rank")

    engine = create_engine_from_env(PROJECT_ROOT)
    try:
        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"connected DB {actual_database!r} does not match {args.confirm_database!r}"
                )
            for statement in sql_statements(DDL_PATH):
                connection.exec_driver_sql(statement)
            existing = int(
                connection.exec_driver_sql("SELECT COUNT(*) FROM business_photo").scalar_one()
            )
            if existing:
                raise RuntimeError(f"business_photo already has {existing:,} rows")
            frame.where(pd.notna(frame), None).to_sql(
                "business_photo", con=connection, if_exists="append", index=False,
                chunksize=args.chunk_size, method="multi"
            )
            loaded = int(
                connection.exec_driver_sql("SELECT COUNT(*) FROM business_photo").scalar_one()
            )
            if loaded != len(frame):
                raise RuntimeError(f"loaded {loaded:,}, expected {len(frame):,}")
            print(f"loaded {loaded:,} business photo rows")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
