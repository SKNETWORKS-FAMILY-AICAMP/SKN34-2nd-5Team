"""Build transparent restaurant candidates for v04 test reviewers.

This is an operational candidate list, not a prediction.  It uses only review
history through each reviewer's selection year, excludes previously reviewed
businesses, and searches within the selection-period P90 activity radius.
When fewer than three category-matched candidates exist, the radius expands to
1.5x and then to a hard 50 km cap.  Results are written as an intermediate
Parquet artifact for later database loading.
"""
from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree


ROOT = Path(__file__).resolve().parents[2]
MODEL_VERSION = "v04"
SELECTION_YEAR = 2018
EARTH_RADIUS_KM = 6_371.0
MAX_RECOMMENDATIONS = 3
MAX_RADIUS_KM = 50.0
GENERIC_CATEGORIES = {
    "restaurants",
    "food",
    "nightlife",
    "shopping",
    "local services",
    "event planning & services",
}


def category_set(value: object) -> frozenset[str]:
    if pd.isna(value):
        return frozenset()
    return frozenset(
        label
        for raw in str(value).split(",")
        if (label := raw.strip().lower()) and label not in GENERIC_CATEGORIES
    )


def load_businesses(interim: Path) -> pd.DataFrame:
    frames = [
        pd.read_parquet(interim / "restaurant_businesses.parquet"),
        pd.read_parquet(interim / "additional_culinary_businesses_v02.parquet"),
    ]
    businesses = pd.concat(frames, ignore_index=True).drop_duplicates(
        "business_id", keep="first"
    )
    businesses = businesses.loc[
        businesses["is_open"].eq(1)
        & businesses["stars"].ge(3.5)
        & businesses["review_count"].ge(10)
        & businesses["latitude"].notna()
        & businesses["longitude"].notna()
    ].copy()
    businesses["category_set"] = businesses["categories"].map(category_set)
    return businesses.loc[businesses["category_set"].map(bool)].reset_index(drop=True)


def load_history(interim: Path, users: set[str]) -> pd.DataFrame:
    columns = ["user_id", "business_id", "stars", "date"]
    reviews = pd.concat(
        [
            pd.read_parquet(interim / "restaurant_reviews.parquet", columns=columns),
            pd.read_parquet(
                interim / "additional_culinary_reviews_v02.parquet", columns=columns
            ),
        ],
        ignore_index=True,
    )
    reviews = reviews.loc[reviews["user_id"].isin(users)].copy()
    reviews["review_date"] = pd.to_datetime(reviews["date"], errors="coerce")
    return reviews.loc[
        reviews["review_date"].notna()
        & reviews["review_date"].dt.year.le(SELECTION_YEAR)
    ]


def preference_maps(
    history: pd.DataFrame, business_categories: dict[str, frozenset[str]]
) -> tuple[dict[str, set[str]], dict[str, dict[str, float]]]:
    visited: dict[str, set[str]] = (
        history.groupby("user_id")["business_id"].agg(set).to_dict()
    )
    scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    positive = history.loc[history["stars"].ge(4)]
    for row in positive.itertuples(index=False):
        labels = business_categories.get(row.business_id, frozenset())
        age = max(0, SELECTION_YEAR - int(row.review_date.year))
        recency_weight = 0.5 + 0.5 * max(0.0, 1.0 - age / 5.0)
        star_weight = 1.25 if float(row.stars) >= 5 else 1.0
        for label in labels:
            scores[row.user_id][label] += recency_weight * star_weight
    return visited, {user_id: dict(values) for user_id, values in scores.items()}


def radius_stages(p90_radius_km: float) -> list[tuple[str, float]]:
    first = min(MAX_RADIUS_KM, max(0.0, float(p90_radius_km)))
    second = min(MAX_RADIUS_KM, first * 1.5)
    stages = [("personal_p90", first)]
    if second > first:
        stages.append(("expanded_1_5x", second))
    if stages[-1][1] < MAX_RADIUS_KM:
        stages.append(("fallback_50km", MAX_RADIUS_KM))
    return stages


def main() -> None:
    interim = ROOT / "data" / "interim"
    cohort = pd.read_parquet(
        interim / "rolling" / "culinary_rolling_cohort_master_v04.parquet"
    )
    cohort = cohort.loc[
        cohort["split_v04"].eq("test")
        & cohort["selection_year"].eq(SELECTION_YEAR),
        ["sample_id", "user_id", "selection_year"],
    ]
    spatial = pd.read_parquet(
        ROOT
        / "data"
        / "processed"
        / "spatial"
        / "reviewer_spatial_summaries_v04.parquet"
    )
    spatial = spatial.loc[
        spatial["period_type"].eq("selection") & spatial["radius_available"],
        ["sample_id", "center_latitude", "center_longitude", "p90_radius_km"],
    ]
    reviewers = cohort.merge(spatial, on="sample_id", how="inner")

    businesses = load_businesses(interim)
    business_categories = businesses.set_index("business_id")["category_set"].to_dict()
    history = load_history(interim, set(reviewers["user_id"]))
    visited, preferences = preference_maps(history, business_categories)

    coordinates = np.radians(businesses[["latitude", "longitude"]].to_numpy())
    tree = BallTree(coordinates, metric="haversine")
    output: list[dict] = []

    for reviewer in reviewers.itertuples(index=False):
        preference = preferences.get(reviewer.user_id, {})
        if not preference:
            continue
        center = np.radians([[reviewer.center_latitude, reviewer.center_longitude]])
        indices, distances = tree.query_radius(
            center,
            r=MAX_RADIUS_KM / EARTH_RADIUS_KM,
            return_distance=True,
            sort_results=True,
        )
        nearby = businesses.iloc[indices[0]].copy()
        nearby["distance_km"] = distances[0] * EARTH_RADIUS_KM
        nearby = nearby.loc[
            ~nearby["business_id"].isin(visited.get(reviewer.user_id, set()))
        ].copy()
        nearby["matched_categories"] = nearby["category_set"].map(
            lambda labels: tuple(
                sorted(labels.intersection(preference), key=preference.get, reverse=True)
            )
        )
        nearby = nearby.loc[nearby["matched_categories"].map(bool)].copy()

        selected_stage = "fallback_50km"
        selected_radius = MAX_RADIUS_KM
        candidates = nearby
        for stage, radius in radius_stages(reviewer.p90_radius_km):
            candidates = nearby.loc[nearby["distance_km"].le(radius)].copy()
            selected_stage, selected_radius = stage, radius
            if len(candidates) >= MAX_RECOMMENDATIONS or radius >= MAX_RADIUS_KM:
                break

        candidates["category_match_score"] = candidates["matched_categories"].map(
            lambda labels: sum(preference[label] for label in labels)
        )
        candidates["primary_category"] = candidates["matched_categories"].str[0]
        candidates = candidates.sort_values(
            ["category_match_score", "distance_km", "stars", "review_count", "business_id"],
            ascending=[False, True, False, False, True],
            kind="mergesort",
        )

        chosen = []
        used_categories: set[str] = set()
        for venue in candidates.itertuples(index=False):
            if venue.primary_category in used_categories:
                continue
            chosen.append(venue)
            used_categories.add(venue.primary_category)
            if len(chosen) == MAX_RECOMMENDATIONS:
                break

        for rank, venue in enumerate(chosen, start=1):
            output.append(
                {
                    "model_version": MODEL_VERSION,
                    "sample_id": reviewer.sample_id,
                    "user_id": reviewer.user_id,
                    "selection_year": int(reviewer.selection_year),
                    "business_id": venue.business_id,
                    "business_name": venue.name,
                    "city": venue.city,
                    "state": venue.state,
                    "distance_km": round(float(venue.distance_km), 2),
                    "matched_categories": ", ".join(venue.matched_categories),
                    "primary_category": venue.primary_category,
                    "category_match_score": round(float(venue.category_match_score), 4),
                    "stars": float(venue.stars),
                    "review_count": int(venue.review_count),
                    "recommendation_rank": rank,
                    "radius_stage": selected_stage,
                    "search_radius_km": round(float(selected_radius), 2),
                    "reason": "미방문 · 긍정 리뷰 카테고리 일치 · 선택연도 이전 이력",
                }
            )

    result = pd.DataFrame(output)
    result = result.sort_values(
        ["sample_id", "recommendation_rank"], kind="mergesort"
    ).reset_index(drop=True)
    path = (
        ROOT
        / "data"
        / "processed"
        / "reviewer_restaurant_recommendations_v04.parquet"
    )
    result.to_parquet(path, index=False)
    covered = result["sample_id"].nunique() if not result.empty else 0
    print(
        f"wrote {len(result):,} candidates for {covered:,}/{len(reviewers):,} "
        f"reviewers to {path}"
    )


if __name__ == "__main__":
    main()
