"""Seed demo business_sponsorships rows for the campaign-slot feature.

This is fixture/demo data for an admin-operated feature that has no real
contract data yet (no payment/CRM integration exists) — not a derived
analytics artifact, so it lives outside v05/pipeline's Yelp-data-derivation
convention. Picks the 4 highest-review-count businesses in each of the 14
v04 states as 'active' sponsors active today, plus 3 extra rows (scheduled/
expiring-soon/expired) in NJ to show every admin-screen status at least once.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_LOAD_DIR = PROJECT_ROOT / "database" / "load"
if str(DATABASE_LOAD_DIR) not in sys.path:
    sys.path.insert(0, str(DATABASE_LOAD_DIR))

from load_v04 import create_engine_from_env, database_name, sql_statements  # noqa: E402


DDL_PATH = PROJECT_ROOT / "v05" / "database" / "ddl" / "025_create_business_sponsorships.sql"
VALID_STATES = (
    "AB", "AZ", "CA", "DE", "FL", "ID", "IL", "IN", "LA", "MO", "NJ", "NV", "PA", "TN",
)
CREATED_BY = "seed_business_sponsorships"


def top_businesses_by_state() -> pd.DataFrame:
    interim = PROJECT_ROOT / "data" / "interim"
    businesses = pd.concat(
        [
            pd.read_parquet(interim / "restaurant_businesses.parquet", columns=["business_id", "state", "review_count"]),
            pd.read_parquet(interim / "additional_culinary_businesses_v02.parquet", columns=["business_id", "state", "review_count"]),
        ],
        ignore_index=True,
    ).drop_duplicates("business_id", keep="first")
    businesses = businesses.loc[businesses["state"].isin(VALID_STATES)]
    ranked = businesses.sort_values(["state", "review_count", "business_id"], ascending=[True, False, True], kind="mergesort")
    return ranked.groupby("state", as_index=False).head(4)


def build_rows() -> list[dict]:
    top = top_businesses_by_state()
    today = date.today()
    rows = []
    for row in top.itertuples(index=False):
        rows.append(
            {
                "business_id": row.business_id,
                "region_state": row.state,
                "start_date": today - timedelta(days=7),
                "end_date": today + timedelta(days=30),
                "priority_tier": 1,
                "status": "active",
                "created_by": CREATED_BY,
            }
        )

    nj_top = top.loc[top["state"].eq("NJ"), "business_id"].tolist()
    nj_extra = (
        top_businesses_by_state()
        .loc[lambda frame: frame["state"].eq("NJ")]
    )
    interim = PROJECT_ROOT / "data" / "interim"
    nj_all = pd.concat(
        [
            pd.read_parquet(interim / "restaurant_businesses.parquet", columns=["business_id", "state", "review_count"]),
            pd.read_parquet(interim / "additional_culinary_businesses_v02.parquet", columns=["business_id", "state", "review_count"]),
        ],
        ignore_index=True,
    ).drop_duplicates("business_id", keep="first")
    nj_all = nj_all.loc[nj_all["state"].eq("NJ") & ~nj_all["business_id"].isin(nj_top)]
    nj_all = nj_all.sort_values(["review_count", "business_id"], ascending=[False, True], kind="mergesort")
    demo_businesses = nj_all.head(3)["business_id"].tolist()

    demo_specs = [
        ("scheduled", today + timedelta(days=7), today + timedelta(days=37)),
        ("active", today, today + timedelta(days=3)),
        ("expired", today - timedelta(days=40), today - timedelta(days=10)),
    ]
    for business_id, (status, start, end) in zip(demo_businesses, demo_specs):
        rows.append(
            {
                "business_id": business_id,
                "region_state": "NJ",
                "start_date": start,
                "end_date": end,
                "priority_tier": 1,
                "status": status,
                "created_by": CREATED_BY,
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo business_sponsorships rows.")
    parser.add_argument("--confirm-database", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = build_rows()
    engine = create_engine_from_env(PROJECT_ROOT)
    try:
        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"connected DB {actual_database!r} does not match confirmation {args.confirm_database!r}"
                )
            for statement in sql_statements(DDL_PATH):
                connection.exec_driver_sql(statement)
            existing = int(
                connection.exec_driver_sql(
                    f"SELECT COUNT(*) FROM business_sponsorships WHERE created_by = %s",
                    (CREATED_BY,),
                ).scalar_one()
            )
            if existing:
                raise RuntimeError(
                    f"business_sponsorships already has {existing:,} seeded rows; no data was appended"
                )
            frame = pd.DataFrame(rows)
            frame.to_sql("business_sponsorships", con=connection, if_exists="append", index=False)
            print(f"seeded {len(frame):,} business_sponsorships rows across {frame['region_state'].nunique()} states")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
