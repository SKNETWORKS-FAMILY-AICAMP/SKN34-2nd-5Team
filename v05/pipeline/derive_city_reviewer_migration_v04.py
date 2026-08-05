"""Build city-level power-reviewer migration counts for v05.

For each v04 test-cohort reviewer (comparison 2017 / selection 2018), picks
the primary review city per period the same way reviewer_radius_service
does for a single reviewer (most reviews, then most venues, then city name),
then counts how many reviewers' primary city changed between the two
periods. This is a measurable contributor to city-level review-supply
change — distinct from, and not a substitute for, city_review_supply's
year-over-year review counts.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MODEL_VERSION = "v04"
SELECTION_YEAR = 2018


def normalize_city(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower()


def primary_cities(activity: pd.DataFrame, businesses: pd.DataFrame) -> pd.DataFrame:
    merged = activity.merge(businesses, on="business_id", how="inner")
    grouped = (
        merged.groupby(["sample_id", "period_type", "state", "city_key"], as_index=False)
        .agg(
            review_count=("review_count", "sum"),
            venue_count=("business_id", "nunique"),
            city=("city", "min"),
        )
    )
    grouped = grouped.sort_values(
        ["sample_id", "period_type", "review_count", "venue_count", "city_key"],
        ascending=[True, True, False, False, True],
        kind="mergesort",
    )
    return grouped.drop_duplicates(["sample_id", "period_type"], keep="first")


def build_migration() -> pd.DataFrame:
    spatial = ROOT / "data" / "processed" / "spatial"
    activity = pd.read_parquet(
        spatial / "reviewer_activity_locations_v04.parquet",
        columns=["sample_id", "period_type", "business_id", "review_count"],
    )
    businesses = pd.read_parquet(
        spatial / "business_locations_v04.parquet",
        columns=["business_id", "state", "city"],
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

    migration = outflow.merge(inflow, on=["state", "city_key"], how="outer")
    migration["outflow_count"] = migration["outflow_count"].fillna(0).astype(int)
    migration["inflow_count"] = migration["inflow_count"].fillna(0).astype(int)
    migration["city"] = migration["city_out"].fillna(migration["city_in"])
    migration["net_migration"] = migration["inflow_count"] - migration["outflow_count"]
    migration.insert(0, "model_version", MODEL_VERSION)
    migration.insert(1, "selection_year", SELECTION_YEAR)
    return migration[
        [
            "model_version", "selection_year", "state", "city_key", "city",
            "outflow_count", "inflow_count", "net_migration",
        ]
    ].sort_values(["state", "city_key"], kind="mergesort").reset_index(drop=True)


def validate(migration: pd.DataFrame) -> None:
    key = ["model_version", "selection_year", "state", "city_key"]
    if migration.duplicated(key).any():
        raise ValueError("duplicate city reviewer-migration key")
    if migration[key + ["city"]].isna().any().any():
        raise ValueError("NULL city reviewer-migration key")
    if (migration["outflow_count"] < 0).any() or (migration["inflow_count"] < 0).any():
        raise ValueError("negative migration counts")


def main() -> None:
    migration = build_migration()
    validate(migration)
    output = ROOT / "data" / "processed" / "city_reviewer_migration_v04.parquet"
    migration.to_parquet(output, index=False)
    moved = int((migration["outflow_count"] + migration["inflow_count"]).sum() // 2)
    print(
        f"wrote {len(migration):,} city migration rows to {output} "
        f"(~{moved:,} reviewer moves detected)"
    )


if __name__ == "__main__":
    main()
