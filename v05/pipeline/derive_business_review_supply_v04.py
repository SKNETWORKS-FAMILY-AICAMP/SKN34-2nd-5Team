"""Build business-level review-supply change for v05 (2017 vs 2018).

Mirrors city_review_supply's per-year review counting, but grouped by
business_id instead of city, and scoped to the fixed comparison/selection
pair (2017/2018) already used everywhere else in v05 — not the full
2009-2018 history that city_review_supply keeps. Covers the same business
universe as the recommendation pipeline (restaurants + selected culinary
visits) so campaign candidate lists can join against it directly.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MODEL_VERSION = "v04"
COMPARISON_YEAR = 2017
SELECTION_YEAR = 2018


def build_supply() -> pd.DataFrame:
    interim = ROOT / "data" / "interim"
    reviews = pd.concat(
        [
            pd.read_parquet(interim / "restaurant_reviews.parquet", columns=["business_id", "date"]),
            pd.read_parquet(
                interim / "additional_culinary_reviews_v02.parquet", columns=["business_id", "date"]
            ),
        ],
        ignore_index=True,
    )
    reviews["review_date"] = pd.to_datetime(reviews["date"], errors="coerce")
    reviews["activity_year"] = reviews["review_date"].dt.year
    reviews = reviews.loc[reviews["activity_year"].isin([COMPARISON_YEAR, SELECTION_YEAR])]

    annual = (
        reviews.groupby(["business_id", "activity_year"], as_index=False)
        .size()
        .rename(columns={"size": "review_count"})
    )
    wide = annual.pivot(index="business_id", columns="activity_year", values="review_count")
    wide = wide.rename(columns={COMPARISON_YEAR: "comparison_count", SELECTION_YEAR: "selection_count"})
    for column in ("comparison_count", "selection_count"):
        if column not in wide:
            wide[column] = pd.NA
    wide = wide.reset_index()

    rows = []
    for year, count_col, previous_col in (
        (COMPARISON_YEAR, "comparison_count", None),
        (SELECTION_YEAR, "selection_count", "comparison_count"),
    ):
        year_rows = wide.loc[wide[count_col].notna(), ["business_id", count_col]].copy()
        year_rows = year_rows.rename(columns={count_col: "review_count"})
        year_rows["review_count"] = year_rows["review_count"].astype(int)
        year_rows["activity_year"] = year
        if previous_col is not None:
            previous = wide.set_index("business_id")[previous_col]
            year_rows["previous_year_review_count"] = year_rows["business_id"].map(previous)
        else:
            year_rows["previous_year_review_count"] = pd.NA
        rows.append(year_rows)

    supply = pd.concat(rows, ignore_index=True)
    has_previous = supply["previous_year_review_count"].notna()
    supply["yoy_review_change"] = pd.NA
    supply["yoy_review_change_rate"] = pd.NA
    supply.loc[has_previous, "yoy_review_change"] = (
        supply.loc[has_previous, "review_count"] - supply.loc[has_previous, "previous_year_review_count"]
    )
    positive_previous = has_previous & (supply["previous_year_review_count"] > 0)
    supply.loc[positive_previous, "yoy_review_change_rate"] = (
        supply.loc[positive_previous, "yoy_review_change"]
        / supply.loc[positive_previous, "previous_year_review_count"]
    )

    supply.insert(0, "model_version", MODEL_VERSION)
    supply["is_comparison_year"] = supply["activity_year"].eq(COMPARISON_YEAR)
    supply["is_selection_year"] = supply["activity_year"].eq(SELECTION_YEAR)
    supply["calculation_method"] = "restaurant_and_culinary_reviews_by_business"
    supply["previous_year_review_count"] = supply["previous_year_review_count"].astype("Int64")
    supply["yoy_review_change"] = supply["yoy_review_change"].astype("Int64")
    supply["yoy_review_change_rate"] = supply["yoy_review_change_rate"].astype("Float64")

    return supply[
        [
            "model_version", "business_id", "activity_year", "review_count",
            "previous_year_review_count", "yoy_review_change", "yoy_review_change_rate",
            "is_comparison_year", "is_selection_year", "calculation_method",
        ]
    ].sort_values(["business_id", "activity_year"], kind="mergesort").reset_index(drop=True)


def validate(supply: pd.DataFrame) -> None:
    key = ["model_version", "business_id", "activity_year"]
    if supply.duplicated(key).any():
        raise ValueError("duplicate business review-supply key")
    if supply[key].isna().any().any():
        raise ValueError("NULL business review-supply key")
    if (supply["review_count"] < 0).any():
        raise ValueError("negative review_count")
    selection = supply.loc[supply["activity_year"].eq(SELECTION_YEAR)]
    if len(selection) < 1000:
        raise ValueError(f"unexpectedly few businesses with {SELECTION_YEAR} reviews: {len(selection)}")


def main() -> None:
    supply = build_supply()
    validate(supply)
    output = ROOT / "data" / "processed" / "business_review_supply_v04.parquet"
    supply.to_parquet(output, index=False)
    declining = supply.loc[
        supply["activity_year"].eq(SELECTION_YEAR) & supply["yoy_review_change_rate"].lt(-0.15)
    ]
    print(
        f"wrote {len(supply):,} business-year rows to {output}; "
        f"{len(declining):,} businesses declined >15% in {SELECTION_YEAR}"
    )


if __name__ == "__main__":
    main()
