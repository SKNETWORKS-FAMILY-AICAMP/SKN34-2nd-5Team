"""Replace only display-context rows after recommendation candidates change."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_LOAD_DIR = PROJECT_ROOT / "database" / "load"
if str(DATABASE_LOAD_DIR) not in sys.path:
    sys.path.insert(0, str(DATABASE_LOAD_DIR))

from load_v04 import create_engine_from_env, database_name  # noqa: E402


TABLE = "business_display_attribute"
ARTIFACT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "business_display_attributes_v01.parquet"
)
COLUMNS = (
    "business_id", "address", "postal_code", "is_open_snapshot", "hours_json",
    "price_range", "takeout", "delivery", "reservations", "outdoor_seating",
    "wifi", "parking_json", "wheelchair_accessible", "alcohol", "source_type",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--confirm-replace", choices=[TABLE], required=True)
    parser.add_argument("--chunk-size", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frame = pd.read_parquet(ARTIFACT_PATH)
    missing = sorted(set(COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    frame = frame.loc[:, COLUMNS].copy()
    if frame["business_id"].isna().any() or frame["business_id"].duplicated().any():
        raise ValueError("invalid business_id key")
    if set(frame["source_type"].dropna().astype(str)) != {"yelp_open_dataset"}:
        raise ValueError("unexpected source_type")

    engine = create_engine_from_env(PROJECT_ROOT)
    try:
        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"connected DB {actual_database!r} does not match {args.confirm_database!r}"
                )
            existing = int(
                connection.exec_driver_sql(f"SELECT COUNT(*) FROM {TABLE}").scalar_one()
            )
            connection.exec_driver_sql(f"DELETE FROM {TABLE}")
            frame.where(pd.notna(frame), None).to_sql(
                TABLE, con=connection, if_exists="append", index=False,
                chunksize=args.chunk_size, method="multi"
            )
            loaded = int(
                connection.exec_driver_sql(f"SELECT COUNT(*) FROM {TABLE}").scalar_one()
            )
            if loaded != len(frame):
                raise RuntimeError(f"loaded {loaded:,}, expected {len(frame):,}")
            print(f"replaced {existing:,} rows with {loaded:,} display attribute rows")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
