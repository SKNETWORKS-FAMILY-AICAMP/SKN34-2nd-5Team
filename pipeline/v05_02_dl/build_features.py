"""Build v04-aligned category, spatial, and rating features for v05_02_dl.

The approved v04 Core 43 data is treated as immutable. Extra features use
only comparison-year (Y-1) and selection-year (Y) reviews. Target-year
(Y+1) activity is retained only for labels already present in the protected
v04 modeling dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VERSION = "v05_02_dl"
EARTH_RADIUS_KM = 6_371.0088

CONFIG_PATH = Path(__file__).with_name("feature_config.json")
CORE_METADATA_PATH = ROOT / "models" / "final_core_hgb_metadata_v02.json"
CORE_DATA_PATH = ROOT / "data" / "processed" / "modeling_dataset_rolling_v04.parquet"

RESTAURANT_REVIEWS_PATH = ROOT / "data" / "interim" / "restaurant_reviews.parquet"
CULINARY_REVIEWS_PATH = (
    ROOT / "data" / "interim" / "additional_culinary_reviews_v02.parquet"
)
RESTAURANT_BUSINESSES_PATH = (
    ROOT / "data" / "interim" / "restaurant_businesses.parquet"
)
CULINARY_BUSINESSES_PATH = (
    ROOT / "data" / "interim" / "additional_culinary_businesses_v02.parquet"
)

OUTPUT_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "modeling_dataset_v04_extended81_v05_02_dl.parquet"
)
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
FEATURE_METADATA_PATH = REPORT_DIR / "feature_build_metadata.json"
FEATURE_VALIDATION_PATH = REPORT_DIR / "feature_validation.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the v04-aligned extended81 dataset for v05_02_dl."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing extended81 parquet after validation.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def load_config() -> tuple[dict, list[str], dict[str, list[str]], list[str]]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    core_metadata = json.loads(CORE_METADATA_PATH.read_text(encoding="utf-8"))
    core_features = list(core_metadata["feature_columns"])
    extra_groups = {
        name: list(columns)
        for name, columns in config["extra_feature_groups"].items()
    }
    extra_features = [
        column
        for columns in extra_groups.values()
        for column in columns
    ]
    if len(core_features) != config["expected_core_features"]:
        raise ValueError("Core feature count differs from the v04 contract")
    if len(extra_features) != 38 or len(set(extra_features)) != 38:
        raise ValueError("Expected 38 unique extended features")
    if len(core_features + extra_features) != config["expected_total_features"]:
        raise ValueError("Expected 81 total features")
    return config, core_features, extra_groups, extra_features


def validate_inputs(overwrite: bool) -> None:
    required = [
        CONFIG_PATH,
        CORE_METADATA_PATH,
        CORE_DATA_PATH,
        RESTAURANT_REVIEWS_PATH,
        CULINARY_REVIEWS_PATH,
        RESTAURANT_BUSINESSES_PATH,
        CULINARY_BUSINESSES_PATH,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n- " + "\n- ".join(missing))
    if OUTPUT_PATH.exists() and not overwrite:
        raise FileExistsError(
            f"{OUTPUT_PATH} already exists; use --overwrite to replace it"
        )


def load_businesses() -> pd.DataFrame:
    columns = ["business_id", "categories", "latitude", "longitude"]
    businesses = pd.concat(
        [
            pd.read_parquet(RESTAURANT_BUSINESSES_PATH, columns=columns),
            pd.read_parquet(CULINARY_BUSINESSES_PATH, columns=columns),
        ],
        ignore_index=True,
    )
    if len(businesses) != 58_156 or businesses["business_id"].nunique() != 58_156:
        raise ValueError("Expected 58,156 unique culinary businesses")
    if businesses["business_id"].duplicated().any():
        raise ValueError("business_id must be unique")
    if businesses["categories"].fillna("").str.strip().eq("").any():
        raise ValueError("All businesses must have categories")
    if not businesses["latitude"].between(-90, 90).all():
        raise ValueError("Invalid latitude")
    if not businesses["longitude"].between(-180, 180).all():
        raise ValueError("Invalid longitude")
    return businesses


def create_review_tables(
    connection: duckdb.DuckDBPyConnection,
    core: pd.DataFrame,
    businesses: pd.DataFrame,
) -> dict[str, int]:
    cohort_map = core[
        ["sample_id", "user_id", "comparison_year", "selection_year"]
    ].copy()
    connection.register("cohort_map", cohort_map)
    connection.register("business_source", businesses)
    review_sources = (
        f"['{sql_path(RESTAURANT_REVIEWS_PATH)}',"
        f"'{sql_path(CULINARY_REVIEWS_PATH)}']"
    )
    connection.execute(
        f"""
        CREATE TEMP TABLE sample_reviews AS
        WITH reviews AS (
            SELECT
                user_id,
                business_id,
                CAST(stars AS DOUBLE) AS stars,
                YEAR(CAST(date AS TIMESTAMP)) AS review_year
            FROM read_parquet({review_sources})
        )
        SELECT
            cohort.sample_id,
            CASE
                WHEN reviews.review_year = cohort.comparison_year
                    THEN 'baseline'
                ELSE 'recent'
            END AS period,
            reviews.business_id,
            reviews.stars
        FROM reviews
        INNER JOIN cohort_map AS cohort
            ON reviews.user_id = cohort.user_id
           AND (
                reviews.review_year = cohort.comparison_year
                OR reviews.review_year = cohort.selection_year
           )
        """
    )
    connection.execute(
        """
        CREATE TEMP TABLE sample_business AS
        SELECT DISTINCT sample_id, period, business_id
        FROM sample_reviews
        """
    )
    connection.execute(
        """
        CREATE TEMP TABLE business_categories AS
        SELECT DISTINCT
            business_id,
            TRIM(category) AS category
        FROM business_source,
        UNNEST(STRING_SPLIT(categories, ',')) AS categories(category)
        WHERE TRIM(category) <> ''
        """
    )
    coverage = connection.execute(
        """
        SELECT
            COUNT(*) AS review_rows,
            COUNT(DISTINCT CASE WHEN period = 'baseline' THEN sample_id END)
                AS baseline_samples,
            COUNT(DISTINCT CASE WHEN period = 'recent' THEN sample_id END)
                AS recent_samples,
            (SELECT COUNT(*) FROM sample_business) AS sample_business_rows
        FROM sample_reviews
        """
    ).fetchone()
    stats = {
        "sample_review_rows": int(coverage[0]),
        "baseline_samples": int(coverage[1]),
        "recent_samples": int(coverage[2]),
        "sample_business_rows": int(coverage[3]),
    }
    if stats["recent_samples"] != len(core):
        raise ValueError("Every v04 sample must have selection-year reviews")
    return stats


def merge_period_features(
    sample_ids: pd.Series,
    period_features: pd.DataFrame,
    names: dict[str, str],
) -> pd.DataFrame:
    baseline = (
        period_features.loc[period_features["period"].eq("baseline")]
        .drop(columns="period")
        .rename(columns={column: f"baseline_{name}" for column, name in names.items()})
    )
    recent = (
        period_features.loc[period_features["period"].eq("recent")]
        .drop(columns="period")
        .rename(columns={column: f"recent_{name}" for column, name in names.items()})
    )
    return (
        pd.DataFrame({"sample_id": sample_ids})
        .merge(baseline, on="sample_id", how="left", validate="one_to_one")
        .merge(recent, on="sample_id", how="left", validate="one_to_one")
    )


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float).div(denominator.replace(0, np.nan).astype(float))
    return result.replace([np.inf, -np.inf], np.nan)


def build_category_features(
    connection: duckdb.DuckDBPyConnection,
    sample_ids: pd.Series,
) -> pd.DataFrame:
    period_features = connection.execute(
        """
        WITH sample_categories AS (
            SELECT DISTINCT
                sample_business.sample_id,
                sample_business.period,
                sample_business.business_id,
                business_categories.category
            FROM sample_business
            INNER JOIN business_categories USING (business_id)
        ),
        category_counts AS (
            SELECT
                sample_id,
                period,
                category,
                COUNT(DISTINCT business_id) AS category_business_count
            FROM sample_categories
            GROUP BY sample_id, period, category
        ),
        category_shares AS (
            SELECT
                *,
                category_business_count
                / SUM(category_business_count) OVER (
                    PARTITION BY sample_id, period
                ) AS category_share
            FROM category_counts
        )
        SELECT
            sample_id,
            period,
            COUNT(*) AS unique_category_count,
            CASE
                WHEN COUNT(*) > 1 THEN
                    SUM(-category_share * LN(category_share)) / LN(COUNT(*))
                ELSE 0.0
            END AS normalized_category_entropy,
            1.0 - SUM(POW(category_share, 2)) AS simpson_category_diversity,
            MAX(category_share) AS top_category_share
        FROM category_shares
        GROUP BY sample_id, period
        """
    ).fetchdf()
    result = merge_period_features(
        sample_ids,
        period_features,
        {
            "unique_category_count": "unique_category_count",
            "normalized_category_entropy": "normalized_category_entropy",
            "simpson_category_diversity": "simpson_category_diversity",
            "top_category_share": "top_category_share",
        },
    )
    result["baseline_unique_category_count"] = (
        result["baseline_unique_category_count"].fillna(0).astype("int16")
    )
    result["recent_unique_category_count"] = (
        result["recent_unique_category_count"].astype("int16")
    )
    result["unique_category_count_diff"] = (
        result["recent_unique_category_count"]
        - result["baseline_unique_category_count"]
    )
    result["unique_category_ratio"] = safe_ratio(
        result["recent_unique_category_count"],
        result["baseline_unique_category_count"],
    )
    result["unique_category_decline_rate"] = 1 - result["unique_category_ratio"]
    result["category_entropy_decline"] = (
        result["baseline_normalized_category_entropy"]
        - result["recent_normalized_category_entropy"]
    )
    result["simpson_diversity_decline"] = (
        result["baseline_simpson_category_diversity"]
        - result["recent_simpson_category_diversity"]
    )
    result["top_category_share_increase"] = (
        result["recent_top_category_share"]
        - result["baseline_top_category_share"]
    )
    return result


def haversine_km(
    latitude_1: pd.Series,
    longitude_1: pd.Series,
    latitude_2: pd.Series,
    longitude_2: pd.Series,
) -> pd.Series:
    lat1 = np.radians(latitude_1.astype(float))
    lon1 = np.radians(longitude_1.astype(float))
    lat2 = np.radians(latitude_2.astype(float))
    lon2 = np.radians(longitude_2.astype(float))
    latitude_delta = lat2 - lat1
    longitude_delta = lon2 - lon1
    value = (
        np.sin(latitude_delta / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(value, 0, 1)))


def build_spatial_features(
    connection: duckdb.DuckDBPyConnection,
    sample_ids: pd.Series,
) -> pd.DataFrame:
    points = connection.execute(
        """
        SELECT
            sample_business.sample_id,
            sample_business.period,
            sample_business.business_id,
            business_source.latitude,
            business_source.longitude
        FROM sample_business
        INNER JOIN business_source USING (business_id)
        """
    ).fetchdf()
    group_keys = ["sample_id", "period"]
    centers = (
        points.groupby(group_keys, as_index=False)
        .agg(
            center_latitude=("latitude", "median"),
            center_longitude=("longitude", "median"),
        )
    )
    points = points.merge(centers, on=group_keys, how="left", validate="many_to_one")
    points["distance_from_center_km"] = haversine_km(
        points["center_latitude"],
        points["center_longitude"],
        points["latitude"],
        points["longitude"],
    )
    period_features = (
        points.groupby(group_keys, as_index=False)
        .agg(
            spatial_business_count=("business_id", "nunique"),
            median_radius_km=("distance_from_center_km", "median"),
            p90_radius_km=("distance_from_center_km", lambda values: values.quantile(0.9)),
            center_latitude=("center_latitude", "first"),
            center_longitude=("center_longitude", "first"),
        )
    )
    result = merge_period_features(
        sample_ids,
        period_features,
        {
            "spatial_business_count": "spatial_business_count",
            "median_radius_km": "median_radius_km",
            "p90_radius_km": "p90_radius_km",
            "center_latitude": "center_latitude",
            "center_longitude": "center_longitude",
        },
    )
    result["baseline_spatial_business_count"] = (
        result["baseline_spatial_business_count"].fillna(0).astype("int16")
    )
    result["recent_spatial_business_count"] = (
        result["recent_spatial_business_count"].astype("int16")
    )
    result["median_radius_decline_km"] = (
        result["baseline_median_radius_km"] - result["recent_median_radius_km"]
    )
    result["p90_radius_decline_km"] = (
        result["baseline_p90_radius_km"] - result["recent_p90_radius_km"]
    )
    result["log_p90_radius_decline"] = (
        np.log1p(result["baseline_p90_radius_km"])
        - np.log1p(result["recent_p90_radius_km"])
    )
    result["center_shift_km"] = haversine_km(
        result["baseline_center_latitude"],
        result["baseline_center_longitude"],
        result["recent_center_latitude"],
        result["recent_center_longitude"],
    )
    result["log_center_shift"] = np.log1p(result["center_shift_km"])
    result["recent_spatial_available"] = (
        result["recent_spatial_business_count"].ge(2).astype("int8")
    )
    return result.drop(
        columns=[
            "baseline_center_latitude",
            "baseline_center_longitude",
            "recent_center_latitude",
            "recent_center_longitude",
        ]
    )


def build_rating_features(
    connection: duckdb.DuckDBPyConnection,
    sample_ids: pd.Series,
) -> pd.DataFrame:
    period_features = connection.execute(
        """
        SELECT
            sample_id,
            period,
            AVG(stars) AS mean_rating,
            STDDEV_POP(stars) AS rating_std,
            AVG(CASE WHEN stars <= 2 THEN 1.0 ELSE 0.0 END) AS low_rating_rate,
            AVG(CASE WHEN stars >= 4 THEN 1.0 ELSE 0.0 END) AS high_rating_rate
        FROM sample_reviews
        GROUP BY sample_id, period
        """
    ).fetchdf()
    result = merge_period_features(
        sample_ids,
        period_features,
        {
            "mean_rating": "mean_rating",
            "rating_std": "rating_std",
            "low_rating_rate": "low_rating_rate",
            "high_rating_rate": "high_rating_rate",
        },
    )
    result["mean_rating_change"] = (
        result["recent_mean_rating"] - result["baseline_mean_rating"]
    )
    result["rating_std_change"] = (
        result["recent_rating_std"] - result["baseline_rating_std"]
    )
    result["low_rating_rate_increase"] = (
        result["recent_low_rating_rate"] - result["baseline_low_rating_rate"]
    )
    result["high_rating_rate_decline"] = (
        result["baseline_high_rating_rate"] - result["recent_high_rating_rate"]
    )
    return result


def validate_extended_dataset(
    core: pd.DataFrame,
    extended: pd.DataFrame,
    config: dict,
    core_features: list[str],
    extra_groups: dict[str, list[str]],
    extra_features: list[str],
) -> pd.DataFrame:
    if len(extended) != config["expected_rows"]:
        raise ValueError(f"Expected {config['expected_rows']:,} rows")
    if not extended["sample_id"].is_unique:
        raise ValueError("sample_id must be unique")
    if extended["sample_id"].tolist() != core["sample_id"].tolist():
        raise ValueError("Row order or sample IDs changed")
    if not extended[core.columns].equals(core):
        raise ValueError("Protected v04 columns changed")
    all_features = core_features + extra_features
    if len(all_features) != 81 or len(set(all_features)) != 81:
        raise ValueError("Feature contract must contain 81 unique columns")
    if set(config["excluded_columns"]) & set(all_features):
        raise ValueError("Forbidden or target-derived columns found in features")
    if set(all_features) - set(extended.columns):
        raise ValueError("Extended feature columns are missing")
    values = extended[all_features].to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("Infinite feature values are not allowed")

    recent_features = [
        column
        for column in extra_features
        if column.startswith("recent_")
    ]
    if extended[recent_features].isna().any().any():
        raise ValueError("Selection-year extended features must be complete")
    if not extended["recent_unique_category_count"].ge(1).all():
        raise ValueError("Every sample needs at least one recent category")
    if not extended["recent_spatial_business_count"].ge(1).all():
        raise ValueError("Every sample needs at least one recent business location")
    if not extended["recent_mean_rating"].between(1, 5).all():
        raise ValueError("Recent mean rating must be between 1 and 5")

    bounded = [
        "baseline_normalized_category_entropy",
        "baseline_simpson_category_diversity",
        "baseline_top_category_share",
        "recent_normalized_category_entropy",
        "recent_simpson_category_diversity",
        "recent_top_category_share",
        "baseline_low_rating_rate",
        "baseline_high_rating_rate",
        "recent_low_rating_rate",
        "recent_high_rating_rate",
    ]
    for column in bounded:
        non_missing = extended[column].dropna()
        if not non_missing.between(-1e-9, 1 + 1e-9).all():
            raise ValueError(f"{column} must be within [0, 1]")

    validation = pd.DataFrame(
        {
            "feature": all_features,
            "group": (
                ["core43"] * len(core_features)
                + [
                    group
                    for group, columns in extra_groups.items()
                    for _ in columns
                ]
            ),
            "dtype": [str(extended[column].dtype) for column in all_features],
            "missing_count": [
                int(extended[column].isna().sum()) for column in all_features
            ],
            "missing_rate": [
                float(extended[column].isna().mean()) for column in all_features
            ],
            "infinite_count": [
                int(np.isinf(extended[column].to_numpy(dtype=float)).sum())
                for column in all_features
            ],
        }
    )
    if len(validation) != 81:
        raise ValueError("Feature validation must have 81 rows")
    return validation


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    validate_inputs(args.overwrite)
    config, core_features, extra_groups, extra_features = load_config()
    core = pd.read_parquet(CORE_DATA_PATH)
    if len(core) != config["expected_rows"]:
        raise ValueError("Protected v04 dataset row count changed")
    businesses = load_businesses()

    connection = duckdb.connect()
    try:
        # Floating-point aggregates must be reproducible across rebuilds.
        connection.execute("SET threads = 1")
        connection.execute("SET preserve_insertion_order = true")
        print("1/5 v04 표본과 Y-1/Y 리뷰 연결", flush=True)
        review_stats = create_review_tables(connection, core, businesses)
        print("2/5 카테고리 다양성 14피처 생성", flush=True)
        category = build_category_features(connection, core["sample_id"])
        print("3/5 맛집 탐방 반경 12피처 생성", flush=True)
        spatial = build_spatial_features(connection, core["sample_id"])
        print("4/5 평점 변화 12피처 생성", flush=True)
        rating = build_rating_features(connection, core["sample_id"])
    finally:
        connection.close()

    extended = core.copy()
    for feature_frame in [category, spatial, rating]:
        extended = extended.merge(
            feature_frame,
            on="sample_id",
            how="left",
            validate="one_to_one",
            sort=False,
        )
    extended = extended.loc[core.index].reset_index(drop=True)
    core = core.reset_index(drop=True)

    print("5/5 extended81 계약 검증 및 저장", flush=True)
    validation = validate_extended_dataset(
        core,
        extended,
        config,
        core_features,
        extra_groups,
        extra_features,
    )
    atomic_write_parquet(extended, OUTPUT_PATH)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    validation.to_csv(FEATURE_VALIDATION_PATH, index=False, encoding="utf-8-sig")

    metadata = {
        "version": VERSION,
        "dataset_version": config["dataset_version"],
        "feature_set": config["feature_set"],
        "row_count": len(extended),
        "column_count": len(extended.columns),
        "feature_count": len(core_features + extra_features),
        "core_feature_count": len(core_features),
        "extra_feature_count": len(extra_features),
        "feature_columns": core_features + extra_features,
        "feature_groups": {
            "core43": core_features,
            **extra_groups,
        },
        "time_structure": config["time_structure"],
        "review_stats": review_stats,
        "input_sha256": {
            "v04_modeling_dataset": sha256(CORE_DATA_PATH),
            "feature_config": sha256(CONFIG_PATH),
        },
        "output_sha256": sha256(OUTPUT_PATH),
        "missing_count_by_group": {
            group: int(validation.loc[validation["group"].eq(group), "missing_count"].sum())
            for group in validation["group"].unique()
        },
        "elapsed_seconds": time.perf_counter() - started,
        "notes": [
            "Extra features use comparison-year and selection-year reviews only.",
            "Target-year columns remain labels and are never model inputs.",
            "Useful, cool, and funny reaction columns are excluded.",
            "A zero baseline business/category count is valid; undefined baseline ratios remain missing.",
        ],
    }
    FEATURE_METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"saved={OUTPUT_PATH}, rows={len(extended):,}, features=81, "
        f"elapsed={metadata['elapsed_seconds']:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
