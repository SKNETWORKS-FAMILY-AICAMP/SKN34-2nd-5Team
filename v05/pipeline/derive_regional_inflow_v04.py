"""Build historical reviewer-region mappings and first cohort-entry counts.

The outputs are intermediate Parquet artifacts for later DB loading. A person
is counted once, in the region mapped at their first v04 cohort selection
year; this describes cohort entry, not a move or a place of residence.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v04.derived_reviewer_activity import (  # noqa: E402
    derive_reviewer_region,
    reviews_in_feature_window,
)


MODEL_VERSION = "v04"


def main() -> None:
    interim = ROOT / "data" / "interim"
    rolling = interim / "rolling" / "culinary_rolling_cohort_master_v04.parquet"
    restaurant_reviews = interim / "restaurant_reviews.parquet"
    culinary_reviews = interim / "additional_culinary_reviews_v02.parquet"
    businesses = interim / "restaurant_businesses.parquet"
    output = ROOT / "data" / "processed"
    output.mkdir(parents=True, exist_ok=True)
    history = output / "reviewer_region_history_v04.parquet"
    newcomers = output / "regional_newcomers_v04.parquet"

    profiles = pd.read_parquet(
        rolling,
        columns=[
            "sample_id", "user_id", "comparison_year", "selection_year",
            "baseline_review_count", "recent_review_count",
        ],
    )
    reviews = pd.concat(
        [
            pd.read_parquet(restaurant_reviews),
            pd.read_parquet(culinary_reviews),
        ],
        ignore_index=True,
    )
    business_lookup = pd.read_parquet(businesses)
    # Reuse the published v04 implementation instead of reproducing its
    # state/city grouping and tie behavior in a second SQL implementation.
    review_window = reviews_in_feature_window(profiles, reviews)
    region = derive_reviewer_region(review_window, business_lookup)
    history_frame = profiles.merge(region, on=["sample_id", "user_id"], how="inner")
    # The published 2018 artifact is the immutable v04 compatibility
    # baseline.  Reusing it avoids the remaining order-sensitive tie cases
    # when the historical all-year frame contains repeated users.
    published_2018 = pd.read_parquet(
        ROOT / "data" / "processed" / "reviewer_region_v04.parquet",
        columns=["sample_id", "user_id", "state", "top_city"],
    )
    history_frame = history_frame.loc[history_frame["selection_year"].ne(2018)]
    history_frame = pd.concat(
        [
            history_frame,
            profiles.loc[profiles["selection_year"].eq(2018)].merge(
                published_2018, on=["sample_id", "user_id"], how="inner"
            ),
        ],
        ignore_index=True,
    )
    history_frame.insert(0, "model_version", MODEL_VERSION)
    history_frame["mapping_method"] = "v04_derive_reviewer_region"
    history_frame.to_parquet(history, index=False)

    first_entry = history_frame.sort_values(["user_id", "selection_year", "sample_id"], kind="mergesort")
    first_entry = first_entry.drop_duplicates("user_id", keep="first")
    newcomers_frame = (
        first_entry.groupby(["model_version", "selection_year", "state"], as_index=False)
        .size()
        .rename(columns={"size": "new_power_reviewers"})
        .sort_values(["selection_year", "state"], kind="mergesort")
    )
    newcomers_frame.to_parquet(newcomers, index=False)
    print(f"wrote {history.name} and {newcomers.name}")


if __name__ == "__main__":
    main()
