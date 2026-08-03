"""Build primary-region restaurant candidates without replacing v04 artifacts.

The model/cohort contract remains v04. This v05 operational derivation separates
geographic activity regions at 50 km, uses the dominant region's P90 as the first
search radius, and keeps the existing 1.5x/50 km fallback.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.neighbors import BallTree

from derive_recommendations_v04 import (
    EARTH_RADIUS_KM,
    MAX_RADIUS_KM,
    MAX_RECOMMENDATIONS,
    MODEL_VERSION,
    ROOT,
    SELECTION_YEAR,
    load_businesses,
    load_history,
    preference_maps,
)


RECOMMENDATION_VERSION = "v05_primary_cluster_radius"
CLUSTER_EPS_KM = 50.0
OUTPUT_PATH = (
    ROOT / "data" / "processed" / "reviewer_restaurant_recommendations_v05.parquet"
)


def haversine_km(lat1, lon1, lat2, lon2):
    lat1 = np.radians(lat1.astype(float))
    lon1 = np.radians(lon1.astype(float))
    lat2 = np.radians(lat2.astype(float))
    lon2 = np.radians(lon2.astype(float))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(value, 0.0, 1.0)))


def primary_cluster_context(reviewers: pd.DataFrame, businesses: pd.DataFrame) -> pd.DataFrame:
    spatial_dir = ROOT / "data" / "processed" / "spatial"
    activity = pd.read_parquet(
        spatial_dir / "reviewer_activity_locations_v04.parquet",
        columns=["sample_id", "period_type", "business_id"],
    )
    activity = activity.loc[activity["period_type"].eq("selection")].copy()
    locations = pd.read_parquet(
        spatial_dir / "business_locations_v04.parquet",
        columns=["business_id", "latitude", "longitude"],
    )
    business_weights = businesses[["business_id", "review_count"]].drop_duplicates(
        "business_id"
    )
    points = activity.merge(locations, on="business_id", how="left").merge(
        business_weights, on="business_id", how="left"
    )
    points = points.merge(
        reviewers[
            [
                "sample_id",
                "center_latitude",
                "center_longitude",
                "observed_p90_radius_km",
            ]
        ],
        on="sample_id",
        how="inner",
    ).dropna(subset=["latitude", "longitude"])
    points = points.drop_duplicates(["sample_id", "business_id"]).copy()
    points["review_count"] = points["review_count"].fillna(0).astype(float)
    contexts = []
    for sample_id, group in points.groupby("sample_id", sort=False):
        group = group.reset_index(drop=True)
        group["cluster_label"] = DBSCAN(
            eps=CLUSTER_EPS_KM / EARTH_RADIUS_KM,
            min_samples=1,
            metric="haversine",
        ).fit_predict(np.radians(group[["latitude", "longitude"]].to_numpy()))
        cluster_summary = (
            group.groupby("cluster_label", sort=True)
            .agg(
                business_count=("business_id", "size"),
                review_count_sum=("review_count", "sum"),
                tie_breaker=("business_id", "min"),
            )
            .reset_index()
            .sort_values(
                ["business_count", "review_count_sum", "tie_breaker"],
                ascending=[False, False, True],
                kind="mergesort",
            )
        )
        cluster_count = int(len(cluster_summary))
        primary_label = int(cluster_summary.iloc[0]["cluster_label"])
        primary = group.loc[group["cluster_label"].eq(primary_label)].copy()
        observed_p90 = float(group["observed_p90_radius_km"].iloc[0])

        if cluster_count == 1:
            center_latitude = float(group["center_latitude"].iloc[0])
            center_longitude = float(group["center_longitude"].iloc[0])
            primary_p90 = observed_p90
        else:
            center_latitude = float(primary["latitude"].median())
            center_longitude = float(primary["longitude"].median())
            primary_distances = haversine_km(
                pd.Series(center_latitude, index=primary.index),
                pd.Series(center_longitude, index=primary.index),
                primary["latitude"],
                primary["longitude"],
            )
            primary_p90 = float(primary_distances.quantile(0.90))

        if not np.isfinite(primary_p90) or primary_p90 <= 0:
            primary_p90 = min(MAX_RADIUS_KM, max(0.1, observed_p90))
        primary_count = int(len(primary))
        contexts.append(
            {
                "sample_id": sample_id,
                "recommendation_center_latitude": center_latitude,
                "recommendation_center_longitude": center_longitude,
                "local_p90_radius_km": primary_p90,
                "travel_outlier_count": int(len(group) - primary_count),
                "activity_cluster_count": cluster_count,
                "primary_cluster_business_count": primary_count,
            }
        )
    return pd.DataFrame(contexts)


def radius_stages(local_p90_radius_km: float) -> list[tuple[str, float]]:
    first = min(MAX_RADIUS_KM, max(0.1, float(local_p90_radius_km)))
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
        ROOT / "data" / "processed" / "spatial" / "reviewer_spatial_summaries_v04.parquet"
    )
    spatial = spatial.loc[
        spatial["period_type"].eq("selection") & spatial["radius_available"],
        ["sample_id", "center_latitude", "center_longitude", "p90_radius_km"],
    ].rename(columns={"p90_radius_km": "observed_p90_radius_km"})
    businesses = load_businesses(interim)
    reviewers = cohort.merge(spatial, on="sample_id", how="inner")
    reviewers = reviewers.merge(
        primary_cluster_context(reviewers, businesses), on="sample_id", how="inner"
    )
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
        center = np.radians(
            [[reviewer.recommendation_center_latitude, reviewer.recommendation_center_longitude]]
        )
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
                sorted(
                    labels.intersection(preference),
                    key=lambda label: (-preference[label], label),
                )
            )
        )
        nearby = nearby.loc[nearby["matched_categories"].map(bool)].copy()

        selected_stage = "fallback_50km"
        selected_radius = MAX_RADIUS_KM
        candidates = nearby
        for stage, radius in radius_stages(reviewer.local_p90_radius_km):
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
                    "recommendation_version": RECOMMENDATION_VERSION,
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
                    "observed_p90_radius_km": round(float(reviewer.observed_p90_radius_km), 2),
                    "local_p90_radius_km": round(float(reviewer.local_p90_radius_km), 2),
                    "travel_outlier_count": int(reviewer.travel_outlier_count),
                    "activity_cluster_count": int(reviewer.activity_cluster_count),
                    "primary_cluster_business_count": int(
                        reviewer.primary_cluster_business_count
                    ),
                    "reason": "미방문 · 긍정 리뷰 카테고리 일치 · 여행성 원거리 분리 로컬 반경",
                }
            )

    result = pd.DataFrame(output).sort_values(
        ["sample_id", "recommendation_rank"], kind="mergesort"
    ).reset_index(drop=True)
    result.to_parquet(OUTPUT_PATH, index=False)
    covered = result["sample_id"].nunique() if not result.empty else 0
    expanded = int(result.loc[result["radius_stage"].ne("personal_p90"), "sample_id"].nunique())
    print(
        f"wrote {len(result):,} candidates for {covered:,}/{len(reviewers):,} reviewers "
        f"to {OUTPUT_PATH}; expanded reviewers={expanded:,}"
    )


if __name__ == "__main__":
    main()
