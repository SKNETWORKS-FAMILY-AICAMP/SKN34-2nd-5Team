"""Build reviewer-level region and monthly activity artifacts for v04.

The React exporter used to calculate these values directly from the large
review parquet files.  This module moves that work into the data pipeline so
the same reviewer-level artifacts can be loaded into MySQL and consumed by
other clients without repeating the derivation.

Only the comparison-year through selection-year feature window is used.
Target-year reviews are deliberately excluded to prevent validation-outcome
leakage into operational screens.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.api.types import is_integer_dtype


MODEL_VERSION = "v04"
EXPECTED_TEST_ROWS = 6_533

US_REGION_CODES = {
    "AK",
    "AL",
    "AR",
    "AZ",
    "CA",
    "CO",
    "CT",
    "DC",
    "DE",
    "FL",
    "GA",
    "HI",
    "IA",
    "ID",
    "IL",
    "IN",
    "KS",
    "KY",
    "LA",
    "MA",
    "MD",
    "ME",
    "MI",
    "MN",
    "MO",
    "MS",
    "MT",
    "NC",
    "ND",
    "NE",
    "NH",
    "NJ",
    "NM",
    "NV",
    "NY",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VA",
    "VT",
    "WA",
    "WI",
    "WV",
    "WY",
}

# Yelp's academic dataset includes Canadian review activity.  AB is present in
# the current v04 Test cohort, so validating against US state codes alone would
# reject a real, observed review-activity region.
CANADIAN_REGION_CODES = {
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NS",
    "NT",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
}

ALLOWED_REGION_CODES = US_REGION_CODES | CANADIAN_REGION_CODES

PROFILE_COLUMNS = [
    "sample_id",
    "user_id",
    "comparison_year",
    "selection_year",
    "baseline_review_count",
    "recent_review_count",
]
REVIEW_COLUMNS = ["user_id", "business_id", "date"]
BUSINESS_COLUMNS = ["business_id", "city", "state"]
REGION_COLUMNS = ["sample_id", "user_id", "state", "top_city"]
MONTHLY_COLUMNS = [
    "sample_id",
    "year_month",
    "review_count",
    "unique_business_count",
]


@dataclass(frozen=True)
class DerivedPaths:
    project_root: Path
    profiles: Path
    restaurant_reviews: Path
    additional_reviews: Path
    businesses: Path
    reviewer_region: Path
    monthly_activity: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="v04 리뷰어 권역·월별 활동 Parquet을 생성합니다."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="SKN34-2nd-5Team 프로젝트 루트",
    )
    parser.add_argument(
        "--expected-profile-rows",
        type=int,
        default=EXPECTED_TEST_ROWS,
        help="최종 Test 프로필 기대 행 수",
    )
    return parser.parse_args()


def _additional_reviews_path(root: Path) -> Path:
    """Prefer the v04 pipeline name while accepting the legacy `_v02` name."""
    canonical = root / "data" / "interim" / "additional_culinary_reviews.parquet"
    legacy = root / "data" / "interim" / "additional_culinary_reviews_v02.parquet"
    if canonical.is_file():
        return canonical
    if legacy.is_file():
        return legacy
    return canonical


def derived_paths(project_root: Path) -> DerivedPaths:
    root = project_root.resolve()
    return DerivedPaths(
        project_root=root,
        profiles=(
            root
            / "data"
            / "processed"
            / "predictions"
            / "final_test_retention_profiles_v04.parquet"
        ),
        restaurant_reviews=(
            root / "data" / "interim" / "restaurant_reviews.parquet"
        ),
        additional_reviews=_additional_reviews_path(root),
        businesses=(root / "data" / "interim" / "restaurant_businesses.parquet"),
        reviewer_region=(
            root / "data" / "processed" / "reviewer_region_v04.parquet"
        ),
        monthly_activity=(
            root / "data" / "processed" / "reviewer_monthly_activity_v04.parquet"
        ),
    )


def require_source_files(paths: DerivedPaths) -> None:
    missing = [
        str(path)
        for path in [
            paths.profiles,
            paths.restaurant_reviews,
            paths.additional_reviews,
            paths.businesses,
        ]
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "권역·월별 활동 생성에 필요한 파일이 없습니다:\n- "
            + "\n- ".join(missing)
            + "\n추가 미식 리뷰는 additional_culinary_reviews.parquet 또는 "
            "legacy additional_culinary_reviews_v02.parquet 이름을 지원합니다."
        )


def _require_columns(
    frame: pd.DataFrame,
    required: list[str],
    name: str,
) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{name}: 필수 컬럼 누락 {missing}")


def load_sources(
    paths: DerivedPaths,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    require_source_files(paths)
    profiles = pd.read_parquet(paths.profiles, columns=PROFILE_COLUMNS)
    restaurant_reviews = pd.read_parquet(
        paths.restaurant_reviews,
        columns=REVIEW_COLUMNS,
    )
    additional_reviews = pd.read_parquet(
        paths.additional_reviews,
        columns=REVIEW_COLUMNS,
    )
    businesses = pd.read_parquet(paths.businesses, columns=BUSINESS_COLUMNS)
    reviews = pd.concat(
        [restaurant_reviews, additional_reviews],
        ignore_index=True,
    )
    return profiles, reviews, businesses


def reviews_in_feature_window(
    profiles: pd.DataFrame,
    reviews: pd.DataFrame,
) -> pd.DataFrame:
    """Attach sample IDs and retain only each sample's feature window."""
    _require_columns(profiles, PROFILE_COLUMNS, "profiles")
    _require_columns(reviews, REVIEW_COLUMNS, "reviews")

    if profiles["sample_id"].isna().any() or not profiles["sample_id"].is_unique:
        raise ValueError("profiles: sample_id는 NULL 없이 고유해야 합니다.")
    if profiles[["user_id", "comparison_year", "selection_year"]].isna().any().any():
        raise ValueError("profiles: 사용자 또는 관찰 연도에 NULL이 있습니다.")
    if (profiles["comparison_year"] > profiles["selection_year"]).any():
        raise ValueError("profiles: comparison_year가 selection_year보다 큽니다.")

    profile_window = profiles[
        ["sample_id", "user_id", "comparison_year", "selection_year"]
    ].copy()
    profile_window["sample_id"] = profile_window["sample_id"].astype(str)
    profile_window["user_id"] = profile_window["user_id"].astype(str)

    review_rows = reviews[REVIEW_COLUMNS].copy()
    review_rows["user_id"] = review_rows["user_id"].astype(str)
    review_rows["date"] = pd.to_datetime(review_rows["date"], errors="coerce")
    review_rows = review_rows.dropna(subset=["date", "business_id"])

    sampled = review_rows.merge(
        profile_window,
        on="user_id",
        how="inner",
        validate="many_to_many",
    )
    sampled["review_year"] = sampled["date"].dt.year
    sampled = sampled.loc[
        sampled["review_year"].between(
            sampled["comparison_year"],
            sampled["selection_year"],
        )
    ].copy()
    return sampled


def derive_monthly_activity(review_window: pd.DataFrame) -> pd.DataFrame:
    """Return one row per sample and active month; zero months are omitted."""
    if review_window.empty:
        return pd.DataFrame(columns=MONTHLY_COLUMNS)

    activity = review_window.copy()
    activity["year_month"] = activity["date"].dt.strftime("%Y-%m")
    monthly = (
        activity.groupby(["sample_id", "year_month"], sort=True)
        .agg(
            review_count=("business_id", "size"),
            unique_business_count=("business_id", "nunique"),
        )
        .reset_index()
        .sort_values(["sample_id", "year_month"], kind="mergesort")
        .reset_index(drop=True)
    )
    monthly["review_count"] = monthly["review_count"].astype("int64")
    monthly["unique_business_count"] = monthly[
        "unique_business_count"
    ].astype("int64")
    return monthly[MONTHLY_COLUMNS]


def derive_reviewer_region(
    review_window: pd.DataFrame,
    businesses: pd.DataFrame,
) -> pd.DataFrame:
    """Return each sample's most-reviewed state and city within that state."""
    _require_columns(businesses, BUSINESS_COLUMNS, "businesses")
    if review_window.empty:
        return pd.DataFrame(columns=REGION_COLUMNS)

    business_lookup = businesses[BUSINESS_COLUMNS].copy()
    if business_lookup["business_id"].isna().any():
        raise ValueError("businesses: business_id NULL이 있습니다.")
    if not business_lookup["business_id"].is_unique:
        raise ValueError("businesses: business_id가 중복됩니다.")

    joined = review_window.merge(
        business_lookup,
        on="business_id",
        how="left",
        validate="many_to_one",
    )
    joined = joined.dropna(subset=["state"]).copy()
    joined["state"] = joined["state"].astype(str).str.strip().str.upper()
    joined["city"] = joined["city"].astype("string").str.strip()
    joined = joined.loc[joined["state"].ne("")]

    state_counts = (
        joined.groupby(["sample_id", "user_id", "state"], sort=True)
        .size()
        .reset_index(name="review_count")
        # Preserve the v04 React exporter's published tie resolution. There
        # are 35 equal-count state ties in the current Test cohort; changing
        # their secondary ordering would alter regional totals even though the
        # underlying reviews and model predictions did not change.
        .sort_values(
            "review_count",
            ascending=False,
            kind="quicksort",
        )
    )
    selected_states = state_counts.drop_duplicates(
        "sample_id",
        keep="first",
    )[["sample_id", "user_id", "state"]]

    reviews_in_selected_state = joined.merge(
        selected_states[["sample_id", "state"]],
        on=["sample_id", "state"],
        how="inner",
        validate="many_to_one",
    ).dropna(subset=["city"])
    reviews_in_selected_state = reviews_in_selected_state.loc[
        reviews_in_selected_state["city"].ne("")
    ]

    city_counts = (
        reviews_in_selected_state.groupby(["sample_id", "city"], sort=True)
        .size()
        .reset_index(name="review_count")
        .sort_values(
            ["sample_id", "review_count", "city"],
            ascending=[True, False, True],
            kind="mergesort",
        )
    )
    top_cities = city_counts.drop_duplicates("sample_id", keep="first")[
        ["sample_id", "city"]
    ].rename(columns={"city": "top_city"})

    reviewer_region = (
        selected_states.merge(
            top_cities,
            on="sample_id",
            how="left",
            validate="one_to_one",
        )
        .sort_values("sample_id", kind="mergesort")
        .reset_index(drop=True)
    )
    return reviewer_region[REGION_COLUMNS]


def derive_outputs(
    profiles: pd.DataFrame,
    reviews: pd.DataFrame,
    businesses: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    review_window = reviews_in_feature_window(profiles, reviews)
    reviewer_region = derive_reviewer_region(review_window, businesses)
    monthly_activity = derive_monthly_activity(review_window)
    return reviewer_region, monthly_activity


def validate_outputs(
    profiles: pd.DataFrame,
    reviewer_region: pd.DataFrame,
    monthly_activity: pd.DataFrame,
    *,
    expected_profile_rows: int | None = None,
) -> dict[str, Any]:
    """Validate the artifact contract without changing source model outputs."""
    _require_columns(profiles, PROFILE_COLUMNS, "profiles")
    _require_columns(reviewer_region, REGION_COLUMNS, "reviewer_region")
    _require_columns(monthly_activity, MONTHLY_COLUMNS, "monthly_activity")

    if expected_profile_rows is not None and len(profiles) != expected_profile_rows:
        raise ValueError(
            f"profiles: {expected_profile_rows:,}행이 아니라 {len(profiles):,}행입니다."
        )

    profile_samples = set(profiles["sample_id"].astype(str))
    region_samples = set(reviewer_region["sample_id"].astype(str))
    monthly_samples = set(monthly_activity["sample_id"].astype(str))

    if reviewer_region["sample_id"].isna().any():
        raise ValueError("reviewer_region: sample_id NULL이 있습니다.")
    if not reviewer_region["sample_id"].is_unique:
        raise ValueError("reviewer_region: sample_id가 중복됩니다.")
    if region_samples != profile_samples:
        missing = len(profile_samples - region_samples)
        unknown = len(region_samples - profile_samples)
        raise ValueError(
            "reviewer_region: 프로필과 sample_id 집합이 다릅니다 "
            f"(누락={missing:,}, 미등록={unknown:,})."
        )
    if reviewer_region[["user_id", "state"]].isna().any().any():
        raise ValueError("reviewer_region: user_id 또는 state NULL이 있습니다.")

    profile_users = profiles.set_index("sample_id")["user_id"].astype(str)
    region_users = reviewer_region.set_index("sample_id")["user_id"].astype(str)
    mismatched_users = int(
        region_users.ne(profile_users.reindex(region_users.index)).sum()
    )
    if mismatched_users:
        raise ValueError(
            f"reviewer_region: sample_id와 user_id 불일치 {mismatched_users:,}건"
        )

    observed_regions = set(reviewer_region["state"].astype(str))
    unknown_regions = sorted(observed_regions - ALLOWED_REGION_CODES)
    if unknown_regions:
        raise ValueError(f"reviewer_region: 알 수 없는 권역 코드 {unknown_regions}")
    nonnull_cities = reviewer_region["top_city"].dropna().astype(str)
    if nonnull_cities.str.strip().eq("").any():
        raise ValueError("reviewer_region: 빈 top_city 문자열이 있습니다.")

    if monthly_activity[["sample_id", "year_month"]].isna().any().any():
        raise ValueError("monthly_activity: 기본 키에 NULL이 있습니다.")
    if monthly_activity.duplicated(["sample_id", "year_month"]).any():
        raise ValueError("monthly_activity: (sample_id, year_month)가 중복됩니다.")
    if monthly_samples != profile_samples:
        missing = len(profile_samples - monthly_samples)
        unknown = len(monthly_samples - profile_samples)
        raise ValueError(
            "monthly_activity: 프로필과 sample_id 집합이 다릅니다 "
            f"(누락={missing:,}, 미등록={unknown:,})."
        )
    if not is_integer_dtype(monthly_activity["review_count"]):
        raise ValueError("monthly_activity: review_count가 정수형이 아닙니다.")
    if not is_integer_dtype(monthly_activity["unique_business_count"]):
        raise ValueError(
            "monthly_activity: unique_business_count가 정수형이 아닙니다."
        )
    if (monthly_activity["review_count"] <= 0).any():
        raise ValueError("monthly_activity: review_count는 양수여야 합니다.")
    if (monthly_activity["unique_business_count"] <= 0).any():
        raise ValueError(
            "monthly_activity: unique_business_count는 양수여야 합니다."
        )
    if (
        monthly_activity["unique_business_count"]
        > monthly_activity["review_count"]
    ).any():
        raise ValueError(
            "monthly_activity: 고유 음식점 수가 리뷰 수보다 큰 행이 있습니다."
        )

    parsed_month = pd.to_datetime(
        monthly_activity["year_month"].astype(str) + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    )
    if parsed_month.isna().any():
        raise ValueError("monthly_activity: year_month 형식 오류가 있습니다.")

    profile_years = profiles.set_index("sample_id")[
        ["comparison_year", "selection_year"]
    ]
    monthly_with_years = monthly_activity[["sample_id"]].join(
        profile_years,
        on="sample_id",
    )
    activity_year = parsed_month.dt.year.reset_index(drop=True)
    outside_window = ~activity_year.between(
        monthly_with_years["comparison_year"].reset_index(drop=True),
        monthly_with_years["selection_year"].reset_index(drop=True),
    )
    if outside_window.any():
        raise ValueError(
            f"monthly_activity: 관찰 구간 밖 행 {int(outside_window.sum()):,}건"
        )

    actual_review_totals = (
        monthly_activity.groupby("sample_id")["review_count"]
        .sum()
        .reindex(profiles["sample_id"], fill_value=0)
    )
    expected_review_totals = (
        profiles.set_index("sample_id")[
            ["baseline_review_count", "recent_review_count"]
        ]
        .sum(axis=1)
        .reindex(profiles["sample_id"])
    )
    actual_values = actual_review_totals.to_numpy(dtype="int64")
    expected_values = expected_review_totals.to_numpy(dtype="int64")
    total_mismatch = int((actual_values != expected_values).sum())
    if total_mismatch:
        raise ValueError(
            "monthly_activity: 프로필 관찰 구간 리뷰 수와 다른 표본 "
            f"{total_mismatch:,}명"
        )

    return {
        "model_version": MODEL_VERSION,
        "profile_rows": len(profiles),
        "region_rows": len(reviewer_region),
        "monthly_rows": len(monthly_activity),
        "monthly_samples": len(monthly_samples),
        "region_codes": sorted(observed_regions),
    }


def write_outputs(
    paths: DerivedPaths,
    reviewer_region: pd.DataFrame,
    monthly_activity: pd.DataFrame,
) -> None:
    paths.reviewer_region.parent.mkdir(parents=True, exist_ok=True)
    reviewer_region.to_parquet(paths.reviewer_region, index=False)
    monthly_activity.to_parquet(paths.monthly_activity, index=False)


def main() -> int:
    args = parse_args()
    paths = derived_paths(args.project_root)
    try:
        profiles, reviews, businesses = load_sources(paths)
        reviewer_region, monthly_activity = derive_outputs(
            profiles,
            reviews,
            businesses,
        )
        summary = validate_outputs(
            profiles,
            reviewer_region,
            monthly_activity,
            expected_profile_rows=args.expected_profile_rows,
        )
        write_outputs(paths, reviewer_region, monthly_activity)
        summary["reviewer_region_path"] = str(paths.reviewer_region)
        summary["monthly_activity_path"] = str(paths.monthly_activity)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
