from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import yaml


MODEL_VERSION = "v04"
EARTH_RADIUS_KM = 6_371.0
EXPECTED_BUSINESS_ROWS = 58_156
EXPECTED_TEST_ROWS = 6_533
EXPECTED_TEST_NO_PRIOR = 1_692


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "v04 테스트 리뷰어의 2017/2018 음식점 활동 좌표와 "
            "중앙값 중심점·P90 활동 반경을 생성합니다."
        )
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="SKN34-2nd-5Team 프로젝트 루트",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="기존 공간 Parquet 산출물을 덮어씁니다.",
    )
    return parser.parse_args()


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


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
    haversine_value = (
        np.sin(latitude_delta / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(longitude_delta / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(
        np.sqrt(np.clip(haversine_value, 0.0, 1.0))
    )


def _resolve_with_legacy_alias(canonical: Path, legacy: Path) -> Path:
    """Prefer the v04 pipeline name while accepting the legacy `_v02` name.

    Mirrors pipeline/v04/derived_reviewer_activity.py's
    `_additional_reviews_path` — same interim data, same historical rename,
    applied here to both the culinary businesses and reviews inputs since
    only a `_v02`-suffixed copy exists on disk for either.
    """
    if canonical.is_file():
        return canonical
    if legacy.is_file():
        return legacy
    return canonical


def required_paths(project_root: Path) -> dict[str, Path]:
    interim_dir = project_root / "data" / "interim"
    return {
        "config": project_root / "configs" / "analysis_config_v04.yaml",
        "restaurant_businesses": interim_dir / "restaurant_businesses.parquet",
        "culinary_businesses": _resolve_with_legacy_alias(
            interim_dir / "additional_culinary_businesses.parquet",
            interim_dir / "additional_culinary_businesses_v02.parquet",
        ),
        "restaurant_reviews": interim_dir / "restaurant_reviews.parquet",
        "culinary_reviews": _resolve_with_legacy_alias(
            interim_dir / "additional_culinary_reviews.parquet",
            interim_dir / "additional_culinary_reviews_v02.parquet",
        ),
        "cohort": (
            interim_dir / "rolling" / "culinary_rolling_cohort_master_v04.parquet"
        ),
        "modeling": (
            project_root
            / "data"
            / "processed"
            / "modeling_dataset_rolling_v04.parquet"
        ),
    }


def output_paths(project_root: Path) -> dict[str, Path]:
    output_dir = project_root / "data" / "processed" / "spatial"
    return {
        "business_locations": output_dir / "business_locations_v04.parquet",
        "activity_locations": (
            output_dir / "reviewer_activity_locations_v04.parquet"
        ),
        "spatial_summaries": (
            output_dir / "reviewer_spatial_summaries_v04.parquet"
        ),
    }


def validate_files(
    inputs: dict[str, Path],
    outputs: dict[str, Path],
    overwrite: bool,
) -> None:
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("필수 파일 누락:\n- " + "\n- ".join(missing))

    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "기존 공간 산출물이 있습니다. 다시 만들려면 --overwrite를 사용하세요:\n- "
            + "\n- ".join(existing)
        )

    next(iter(outputs.values())).parent.mkdir(parents=True, exist_ok=True)


def read_config(config_path: Path) -> tuple[int, str]:
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    test_selection_year = int(config["cohort"]["test_selection_year"])
    business_scope = str(config["business_scope"]["scope"])
    if test_selection_year != 2018:
        raise ValueError(
            f"v04 테스트 선정 연도가 2018년이 아닙니다: {test_selection_year}"
        )
    return test_selection_year, business_scope


def build_business_locations(
    connection: duckdb.DuckDBPyConnection,
    inputs: dict[str, Path],
    business_scope: str,
) -> pd.DataFrame:
    restaurant_path = sql_path(inputs["restaurant_businesses"])
    culinary_path = sql_path(inputs["culinary_businesses"])
    business_locations = connection.execute(
        f"""
        SELECT
            business_id,
            name,
            address,
            city,
            state,
            postal_code,
            CAST(latitude AS DOUBLE) AS latitude,
            CAST(longitude AS DOUBLE) AS longitude,
            categories,
            'restaurant' AS location_scope
        FROM read_parquet('{restaurant_path}')

        UNION ALL

        SELECT
            business_id,
            name,
            address,
            city,
            state,
            postal_code,
            CAST(latitude AS DOUBLE) AS latitude,
            CAST(longitude AS DOUBLE) AS longitude,
            categories,
            'selected_culinary_visit' AS location_scope
        FROM read_parquet('{culinary_path}')
        """
    ).fetchdf()
    business_locations.insert(0, "business_scope", business_scope)

    if len(business_locations) != EXPECTED_BUSINESS_ROWS:
        raise ValueError(
            "음식점 수가 예상값과 다릅니다: "
            f"{len(business_locations):,} != {EXPECTED_BUSINESS_ROWS:,}"
        )
    if business_locations["business_id"].isna().any():
        raise ValueError("business_locations에 business_id NULL이 있습니다.")
    if not business_locations["business_id"].is_unique:
        raise ValueError("business_locations에 중복 business_id가 있습니다.")
    if business_locations[["latitude", "longitude"]].isna().any().any():
        raise ValueError("business_locations에 위도 또는 경도 NULL이 있습니다.")
    if not business_locations["latitude"].between(-90, 90).all():
        raise ValueError("유효 범위를 벗어난 위도가 있습니다.")
    if not business_locations["longitude"].between(-180, 180).all():
        raise ValueError("유효 범위를 벗어난 경도가 있습니다.")
    return business_locations


def build_activity_locations(
    connection: duckdb.DuckDBPyConnection,
    inputs: dict[str, Path],
    selection_year: int,
) -> pd.DataFrame:
    cohort_path = sql_path(inputs["cohort"])
    restaurant_review_path = sql_path(inputs["restaurant_reviews"])
    culinary_review_path = sql_path(inputs["culinary_reviews"])
    comparison_start = f"{selection_year - 1}-01-01"
    selection_end = f"{selection_year + 1}-01-01"

    activity_locations = connection.execute(
        f"""
        WITH test_cohort AS (
            SELECT
                sample_id,
                user_id,
                comparison_year,
                selection_year
            FROM read_parquet('{cohort_path}')
            WHERE split_v04 = 'test'
              AND selection_year = {selection_year}
        ),
        reviews AS (
            SELECT
                user_id,
                business_id,
                CAST(date AS TIMESTAMP) AS review_ts
            FROM read_parquet('{restaurant_review_path}')
            WHERE CAST(date AS TIMESTAMP) >= TIMESTAMP '{comparison_start}'
              AND CAST(date AS TIMESTAMP) < TIMESTAMP '{selection_end}'

            UNION ALL

            SELECT
                user_id,
                business_id,
                CAST(date AS TIMESTAMP) AS review_ts
            FROM read_parquet('{culinary_review_path}')
            WHERE CAST(date AS TIMESTAMP) >= TIMESTAMP '{comparison_start}'
              AND CAST(date AS TIMESTAMP) < TIMESTAMP '{selection_end}'
        )
        SELECT
            '{MODEL_VERSION}' AS model_version,
            cohort.sample_id,
            CASE
                WHEN YEAR(reviews.review_ts) = cohort.comparison_year
                    THEN 'comparison'
                WHEN YEAR(reviews.review_ts) = cohort.selection_year
                    THEN 'selection'
            END AS period_type,
            CAST(YEAR(reviews.review_ts) AS SMALLINT) AS activity_year,
            reviews.business_id,
            CAST(COUNT(*) AS INTEGER) AS review_count,
            MIN(CAST(reviews.review_ts AS DATE)) AS first_review_date,
            MAX(CAST(reviews.review_ts AS DATE)) AS last_review_date
        FROM test_cohort AS cohort
        INNER JOIN reviews
            ON reviews.user_id = cohort.user_id
           AND YEAR(reviews.review_ts) IN (
               cohort.comparison_year,
               cohort.selection_year
           )
        GROUP BY
            cohort.sample_id,
            period_type,
            activity_year,
            reviews.business_id
        ORDER BY
            cohort.sample_id,
            activity_year,
            reviews.business_id
        """
    ).fetchdf()

    key_columns = [
        "model_version",
        "sample_id",
        "period_type",
        "business_id",
    ]
    if activity_locations[key_columns].isna().any().any():
        raise ValueError("reviewer_activity_locations의 필수 키에 NULL이 있습니다.")
    if activity_locations.duplicated(key_columns).any():
        raise ValueError("reviewer_activity_locations에 중복 복합 키가 있습니다.")
    if not activity_locations["period_type"].isin(
        ["comparison", "selection"]
    ).all():
        raise ValueError("알 수 없는 period_type이 있습니다.")
    return activity_locations


def build_spatial_summaries(
    connection: duckdb.DuckDBPyConnection,
    business_locations: pd.DataFrame,
    activity_locations: pd.DataFrame,
) -> pd.DataFrame:
    connection.register("business_locations_frame", business_locations)
    connection.register("activity_locations_frame", activity_locations)
    spatial_summaries = connection.execute(
        f"""
        WITH located_activity AS (
            SELECT
                activity.model_version,
                activity.sample_id,
                activity.period_type,
                activity.activity_year,
                activity.business_id,
                activity.review_count,
                business.latitude,
                business.longitude
            FROM activity_locations_frame AS activity
            INNER JOIN business_locations_frame AS business
                ON business.business_id = activity.business_id
        ),
        centers AS (
            SELECT
                model_version,
                sample_id,
                period_type,
                activity_year,
                MEDIAN(latitude) AS center_latitude,
                MEDIAN(longitude) AS center_longitude
            FROM located_activity
            GROUP BY
                model_version,
                sample_id,
                period_type,
                activity_year
        ),
        distances AS (
            SELECT
                activity.model_version,
                activity.sample_id,
                activity.period_type,
                activity.activity_year,
                activity.business_id,
                activity.review_count,
                centers.center_latitude,
                centers.center_longitude,
                2.0 * {EARTH_RADIUS_KM} * ASIN(
                    SQRT(
                        LEAST(
                            1.0,
                            POWER(
                                SIN(
                                    RADIANS(
                                        activity.latitude
                                        - centers.center_latitude
                                    ) / 2.0
                                ),
                                2
                            )
                            + COS(RADIANS(centers.center_latitude))
                            * COS(RADIANS(activity.latitude))
                            * POWER(
                                SIN(
                                    RADIANS(
                                        activity.longitude
                                        - centers.center_longitude
                                    ) / 2.0
                                ),
                                2
                            )
                        )
                    )
                ) AS distance_km
            FROM located_activity AS activity
            INNER JOIN centers
                ON centers.model_version = activity.model_version
               AND centers.sample_id = activity.sample_id
               AND centers.period_type = activity.period_type
        )
        SELECT
            model_version,
            sample_id,
            period_type,
            activity_year,
            center_latitude,
            center_longitude,
            CAST(COUNT(*) AS INTEGER) AS spatial_business_count,
            CAST(SUM(review_count) AS INTEGER) AS activity_review_count,
            MEDIAN(distance_km) AS median_radius_km,
            AVG(distance_km) AS mean_radius_km,
            QUANTILE_CONT(distance_km, 0.90) AS p90_radius_km,
            MAX(distance_km) AS max_radius_km,
            CAST(COUNT(*) >= 2 AS BOOLEAN) AS radius_available,
            'median_center_haversine_p90' AS calculation_method,
            {EARTH_RADIUS_KM} AS earth_radius_km
        FROM distances
        GROUP BY
            model_version,
            sample_id,
            period_type,
            activity_year,
            center_latitude,
            center_longitude
        ORDER BY
            sample_id,
            activity_year
        """
    ).fetchdf()

    comparison = spatial_summaries.loc[
        spatial_summaries["period_type"].eq("comparison"),
        [
            "sample_id",
            "center_latitude",
            "center_longitude",
            "p90_radius_km",
            "radius_available",
        ],
    ].rename(
        columns={
            "center_latitude": "comparison_center_latitude",
            "center_longitude": "comparison_center_longitude",
            "p90_radius_km": "comparison_p90_radius_km",
            "radius_available": "comparison_radius_available",
        }
    )
    selection_mask = spatial_summaries["period_type"].eq("selection")
    selection = spatial_summaries.loc[
        selection_mask,
        ["sample_id", "center_latitude", "center_longitude", "p90_radius_km"],
    ].merge(comparison, on="sample_id", how="left")

    comparable_radius = (
        selection["comparison_radius_available"].fillna(False)
        & selection["comparison_p90_radius_km"].gt(0)
    )
    selection["radius_change_km"] = (
        selection["p90_radius_km"] - selection["comparison_p90_radius_km"]
    ).where(comparable_radius)
    selection["radius_change_rate"] = (
        selection["radius_change_km"]
        / selection["comparison_p90_radius_km"]
    ).where(comparable_radius)
    has_comparison_center = selection[
        [
            "comparison_center_latitude",
            "comparison_center_longitude",
        ]
    ].notna().all(axis=1)
    selection["center_shift_km"] = haversine_km(
        selection["comparison_center_latitude"],
        selection["comparison_center_longitude"],
        selection["center_latitude"],
        selection["center_longitude"],
    ).where(has_comparison_center)

    change_columns = [
        "radius_change_km",
        "radius_change_rate",
        "center_shift_km",
    ]
    spatial_summaries[change_columns] = np.nan
    change_values = selection.set_index("sample_id")[change_columns]
    selection_sample_ids = spatial_summaries.loc[
        selection_mask, "sample_id"
    ]
    spatial_summaries.loc[selection_mask, change_columns] = (
        change_values.reindex(selection_sample_ids).to_numpy()
    )

    key_columns = ["model_version", "sample_id", "period_type"]
    if spatial_summaries[key_columns].isna().any().any():
        raise ValueError("reviewer_spatial_summaries의 필수 키에 NULL이 있습니다.")
    if spatial_summaries.duplicated(key_columns).any():
        raise ValueError("reviewer_spatial_summaries에 중복 복합 키가 있습니다.")
    return spatial_summaries


def validate_outputs(
    connection: duckdb.DuckDBPyConnection,
    inputs: dict[str, Path],
    activity_locations: pd.DataFrame,
    spatial_summaries: pd.DataFrame,
    selection_year: int,
) -> None:
    modeling_path = sql_path(inputs["modeling"])
    expected_counts = connection.execute(
        f"""
        SELECT
            sample_id,
            CAST(baseline_unique_business_count AS BIGINT)
                AS expected_comparison_business_count,
            CAST(recent_unique_business_count AS BIGINT)
                AS expected_selection_business_count
        FROM read_parquet('{modeling_path}')
        WHERE split_v04 = 'test'
          AND selection_year = {selection_year}
        """
    ).fetchdf()
    if len(expected_counts) != EXPECTED_TEST_ROWS:
        raise ValueError(
            f"v04 test 모델링 표본 수가 {EXPECTED_TEST_ROWS:,}명이 아닙니다."
        )

    actual_counts = (
        activity_locations.groupby(
            ["sample_id", "period_type"], observed=True
        )["business_id"]
        .nunique()
        .unstack(fill_value=0)
        .rename(
            columns={
                "comparison": "actual_comparison_business_count",
                "selection": "actual_selection_business_count",
            }
        )
        .reset_index()
    )
    for column in [
        "actual_comparison_business_count",
        "actual_selection_business_count",
    ]:
        if column not in actual_counts:
            actual_counts[column] = 0

    count_check = expected_counts.merge(
        actual_counts,
        on="sample_id",
        how="left",
    ).fillna(
        {
            "actual_comparison_business_count": 0,
            "actual_selection_business_count": 0,
        }
    )
    comparison_mismatch = count_check[
        "expected_comparison_business_count"
    ].ne(count_check["actual_comparison_business_count"])
    selection_mismatch = count_check[
        "expected_selection_business_count"
    ].ne(count_check["actual_selection_business_count"])
    if comparison_mismatch.any() or selection_mismatch.any():
        raise ValueError(
            "기존 43개 피처의 고유 음식점 수와 공간 산출물의 음식점 수가 "
            "일치하지 않습니다: "
            f"comparison={int(comparison_mismatch.sum()):,}, "
            f"selection={int(selection_mismatch.sum()):,}"
        )

    selection_rows = int(
        spatial_summaries["period_type"].eq("selection").sum()
    )
    comparison_rows = int(
        spatial_summaries["period_type"].eq("comparison").sum()
    )
    expected_comparison_rows = EXPECTED_TEST_ROWS - EXPECTED_TEST_NO_PRIOR
    if selection_rows != EXPECTED_TEST_ROWS:
        raise ValueError(
            "2018년 공간 요약 수가 예상값과 다릅니다: "
            f"{selection_rows:,} != {EXPECTED_TEST_ROWS:,}"
        )
    if comparison_rows != expected_comparison_rows:
        raise ValueError(
            "2017년 공간 요약 수가 예상값과 다릅니다: "
            f"{comparison_rows:,} != {expected_comparison_rows:,}"
        )

    numeric_columns = [
        "center_latitude",
        "center_longitude",
        "median_radius_km",
        "mean_radius_km",
        "p90_radius_km",
        "max_radius_km",
    ]
    if not np.isfinite(
        spatial_summaries[numeric_columns].to_numpy(dtype=float)
    ).all():
        raise ValueError("공간 요약의 핵심 수치에 NULL 또는 무한대가 있습니다.")


def write_parquet(frame: pd.DataFrame, path: Path) -> None:
    temporary_path = path.with_suffix(".tmp.parquet")
    frame.to_parquet(temporary_path, index=False)
    temporary_path.replace(path)


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    inputs = required_paths(project_root)
    outputs = output_paths(project_root)

    try:
        validate_files(inputs, outputs, args.overwrite)
        selection_year, business_scope = read_config(inputs["config"])

        connection = duckdb.connect()
        try:
            print("1/4 음식점 위치 데이터 생성 중...")
            business_locations = build_business_locations(
                connection,
                inputs,
                business_scope,
            )

            print("2/4 v04 테스트 리뷰어 활동 위치 생성 중...")
            activity_locations = build_activity_locations(
                connection,
                inputs,
                selection_year,
            )

            print("3/4 중앙값 중심점과 P90 활동 반경 계산 중...")
            spatial_summaries = build_spatial_summaries(
                connection,
                business_locations,
                activity_locations,
            )

            print("4/4 기존 고유 음식점 피처와 교차 검증 중...")
            validate_outputs(
                connection,
                inputs,
                activity_locations,
                spatial_summaries,
                selection_year,
            )
        finally:
            connection.close()

        write_parquet(
            business_locations,
            outputs["business_locations"],
        )
        write_parquet(
            activity_locations,
            outputs["activity_locations"],
        )
        write_parquet(
            spatial_summaries,
            outputs["spatial_summaries"],
        )

        print("\n공간 산출물 생성 완료")
        print(
            "- business_locations: "
            f"{len(business_locations):,} rows -> "
            f"{outputs['business_locations']}"
        )
        print(
            "- reviewer_activity_locations: "
            f"{len(activity_locations):,} rows -> "
            f"{outputs['activity_locations']}"
        )
        print(
            "- reviewer_spatial_summaries: "
            f"{len(spatial_summaries):,} rows -> "
            f"{outputs['spatial_summaries']}"
        )
        print("- 기존 모델 43개 피처 변경 없음")
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
