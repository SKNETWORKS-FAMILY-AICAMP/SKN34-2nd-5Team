"""Build development-only Core4 sequences and lifecycle features for v05_05.

The final Test cohort (selection year 2018) is deliberately never loaded into
the generated artifacts. User snapshot fields other than ``yelping_since`` and
the year-valued ``elite`` history are not used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VERSION = "v05_05_dl"
CONFIG_PATH = Path(__file__).with_name("config.json")
SOURCE_PATH = ROOT / "data" / "processed" / "modeling_dataset_rolling_v05_ml.parquet"
RESTAURANT_REVIEWS_PATH = ROOT / "data" / "interim" / "restaurant_reviews.parquet"
CULINARY_REVIEWS_PATH = ROOT / "data" / "interim" / "additional_culinary_reviews_v02.parquet"
OUTPUT_DIR = ROOT / "data" / "processed" / "experiments"
LIFECYCLE_PATH = OUTPUT_DIR / "lifecycle_features_v05_05.parquet"
SEQUENCE_PATH = OUTPUT_DIR / "monthly_core4_sequence_v05_05.parquet"
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
METADATA_PATH = REPORT_DIR / "feature_build_metadata.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-json",
        required=True,
        type=Path,
        help="Path to yelp_academic_dataset_user.json",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def load_development_cohort() -> pd.DataFrame:
    columns = [
        "sample_id",
        "user_id",
        "comparison_year",
        "selection_year",
        "baseline_review_count",
        "recent_review_count",
    ]
    cohort = pd.read_parquet(
        SOURCE_PATH,
        columns=columns,
        filters=[("selection_year", "<=", 2017)],
    )
    cohort = cohort.sort_values("sample_id", kind="stable").reset_index(drop=True)
    if len(cohort) != 31_420:
        raise ValueError(f"Expected 31,420 development rows, found {len(cohort):,}")
    if not cohort["sample_id"].is_unique:
        raise ValueError("Development sample_id must be unique")
    if cohort["selection_year"].max() >= 2018:
        raise ValueError("Final Test row entered the development cohort")
    if set(cohort["selection_year"].unique()) != set(range(2010, 2018)):
        raise ValueError("Unexpected development selection years")
    return cohort


def load_user_fields(user_json: Path, users: pd.DataFrame) -> pd.DataFrame:
    connection = duckdb.connect()
    try:
        connection.execute("SET threads = 4")
        connection.register("development_users", users)
        result = connection.execute(
            f"""
            SELECT source.user_id, source.yelping_since, source.elite
            FROM read_json(
                '{sql_path(user_json)}',
                format = 'newline_delimited',
                columns = {{
                    user_id: 'VARCHAR',
                    yelping_since: 'VARCHAR',
                    elite: 'VARCHAR'
                }}
            ) AS source
            INNER JOIN development_users AS wanted
                ON source.user_id = wanted.user_id
            """
        ).fetchdf()
    finally:
        connection.close()
    if result["user_id"].duplicated().any():
        raise ValueError("Raw User JSON contains duplicate cohort users")
    if len(result) != len(users):
        missing = set(users["user_id"]) - set(result["user_id"])
        raise ValueError(f"Missing {len(missing):,} development users in User JSON")
    return result


def parse_elite_years(value: object) -> frozenset[int]:
    if value is None or pd.isna(value):
        return frozenset()
    years: set[int] = set()
    for token in str(value).split(","):
        token = token.strip()
        if not token:
            continue
        try:
            year = int(token)
        except ValueError as error:
            raise ValueError(f"Invalid Elite year token: {token!r}") from error
        # The distributed Yelp snapshot contains malformed ``20,20`` tokens
        # for some recent Elite histories. They are not valid four-digit years
        # and must not be guessed or mapped to a historical selection year.
        if year < 1900 or year > 2100:
            continue
        years.add(year)
    return frozenset(years)


def has_invalid_elite_token(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    for token in str(value).split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit() or not 1900 <= int(token) <= 2100:
            return True
    return False


def lifecycle_row(elite_years: frozenset[int], selection_year: int) -> tuple[int, int, int, int]:
    # Future Elite years in the snapshot are excluded for every user-year sample.
    observed = {year for year in elite_years if year <= selection_year}
    prior_count = sum(year < selection_year for year in observed)
    current = int(selection_year in observed)
    last_year = max(observed) if observed else None
    years_since_last = selection_year - last_year if last_year is not None else -1
    streak = 0
    if current:
        year = selection_year
        while year in observed:
            streak += 1
            year -= 1
    return prior_count, current, years_since_last, streak


def build_lifecycle(cohort: pd.DataFrame, user_json: Path) -> tuple[pd.DataFrame, dict]:
    users = cohort[["user_id"]].drop_duplicates().reset_index(drop=True)
    raw = load_user_fields(user_json, users)
    raw["yelping_since"] = pd.to_datetime(raw["yelping_since"], errors="raise")
    invalid_elite_token_users = int(raw["elite"].map(has_invalid_elite_token).sum())
    raw["elite_years"] = raw["elite"].map(parse_elite_years)
    joined = cohort[["sample_id", "user_id", "selection_year"]].merge(
        raw[["user_id", "yelping_since", "elite_years"]],
        on="user_id",
        how="left",
        validate="many_to_one",
    )
    cutoff = pd.to_datetime((joined["selection_year"] + 1).astype(str) + "-01-01")
    account_age = (cutoff - joined["yelping_since"]).dt.days
    if account_age.isna().any() or account_age.lt(0).any():
        raise ValueError("Invalid account age at selection cutoff")
    values = [
        lifecycle_row(years, int(year))
        for years, year in zip(joined["elite_years"], joined["selection_year"])
    ]
    lifecycle_values = pd.DataFrame(
        values,
        columns=[
            "elite_year_count_prior",
            "is_elite_selection_year",
            "years_since_last_elite",
            "recent_elite_streak",
        ],
    )
    output = pd.concat(
        [
            joined[["sample_id", "selection_year"]].reset_index(drop=True),
            account_age.rename("account_age_days").reset_index(drop=True),
            lifecycle_values,
        ],
        axis=1,
    )
    integer_columns = [column for column in output.columns if column != "sample_id"]
    output[integer_columns] = output[integer_columns].astype("int32")
    if not output["sample_id"].is_unique or len(output) != len(cohort):
        raise ValueError("Lifecycle output key contract changed")
    if set(output["is_elite_selection_year"].unique()) - {0, 1}:
        raise ValueError("Selection-year Elite flag must be binary")
    # Evidence that future snapshot years existed but were excluded from features.
    latest_sample_year = joined["selection_year"].to_numpy()
    future_snapshot_rows = sum(
        any(elite_year > selection_year for elite_year in elite_years)
        for elite_years, selection_year in zip(joined["elite_years"], latest_sample_year)
    )
    diagnostics = {
        "unique_users": len(users),
        "users_with_invalid_elite_tokens_excluded": invalid_elite_token_users,
        "samples_with_future_elite_years_excluded": int(future_snapshot_rows),
        "samples_without_observed_elite_history": int(
            output["years_since_last_elite"].eq(-1).sum()
        ),
        "selection_year_elite_samples": int(output["is_elite_selection_year"].sum()),
    }
    return output, diagnostics


def build_active_months(cohort: pd.DataFrame) -> pd.DataFrame:
    registered = cohort[["sample_id", "user_id", "comparison_year", "selection_year"]]
    sources = (
        f"['{sql_path(RESTAURANT_REVIEWS_PATH)}',"
        f"'{sql_path(CULINARY_REVIEWS_PATH)}']"
    )
    connection = duckdb.connect()
    try:
        connection.execute("SET threads = 4")
        connection.register("development_cohort", registered)
        active = connection.execute(
            f"""
            WITH reviews AS (
                SELECT
                    user_id,
                    business_id,
                    CAST(date AS TIMESTAMP) AS review_ts,
                    YEAR(CAST(date AS TIMESTAMP)) AS review_year,
                    MONTH(CAST(date AS TIMESTAMP)) AS review_month
                FROM read_parquet({sources})
            ),
            matched AS (
                SELECT
                    cohort.sample_id,
                    (
                        (reviews.review_year - cohort.comparison_year) * 12
                        + reviews.review_month - 1
                    )::SMALLINT AS month_index,
                    reviews.business_id,
                    reviews.review_ts
                FROM reviews
                INNER JOIN development_cohort AS cohort
                    ON reviews.user_id = cohort.user_id
                   AND reviews.review_year BETWEEN
                       cohort.comparison_year AND cohort.selection_year
            ),
            with_interval AS (
                SELECT
                    *,
                    DATE_DIFF(
                        'second',
                        LAG(review_ts) OVER (
                            PARTITION BY sample_id, month_index
                            ORDER BY review_ts, business_id
                        ),
                        review_ts
                    ) / 86400.0 AS interval_days
                FROM matched
            )
            SELECT
                sample_id,
                month_index,
                COUNT(*)::INTEGER AS monthly_review_count,
                COUNT(DISTINCT business_id)::INTEGER
                    AS monthly_unique_business_count,
                COALESCE(AVG(interval_days), 0.0)::DOUBLE
                    AS monthly_mean_interval_days
            FROM with_interval
            GROUP BY sample_id, month_index
            ORDER BY sample_id, month_index
            """
        ).fetchdf()
    finally:
        connection.close()
    if not active["month_index"].between(0, 23).all():
        raise ValueError("Core4 month index escaped 0..23")
    return active


def complete_sequence(cohort: pd.DataFrame, active: pd.DataFrame) -> pd.DataFrame:
    grid = pd.DataFrame(
        {
            "sample_id": np.repeat(cohort["sample_id"].to_numpy(), 24),
            "comparison_year": np.repeat(
                cohort["comparison_year"].to_numpy(dtype=np.int16), 24
            ),
            "month_index": np.tile(np.arange(24, dtype=np.int8), len(cohort)),
        }
    )
    grid = grid.merge(
        active,
        on=["sample_id", "month_index"],
        how="left",
        validate="one_to_one",
        sort=False,
    )
    count_columns = ["monthly_review_count", "monthly_unique_business_count"]
    grid[count_columns] = grid[count_columns].fillna(0).astype("int32")
    grid["monthly_mean_interval_days"] = (
        grid["monthly_mean_interval_days"].fillna(0.0).astype("float32")
    )
    grid["monthly_active"] = grid["monthly_review_count"].gt(0).astype("int8")
    year = grid["comparison_year"] + grid["month_index"].floordiv(12)
    month = grid["month_index"].mod(12) + 1
    grid["year_month"] = year.astype(str) + "-" + month.astype(str).str.zfill(2)
    output = grid[
        [
            "sample_id",
            "month_index",
            "year_month",
            "monthly_review_count",
            "monthly_active",
            "monthly_unique_business_count",
            "monthly_mean_interval_days",
        ]
    ]
    if len(output) != len(cohort) * 24:
        raise ValueError("Every development sample must have exactly 24 months")
    if output.duplicated(["sample_id", "month_index"]).any():
        raise ValueError("Duplicate development sample-month")
    if output["sample_id"].drop_duplicates().tolist() != cohort["sample_id"].tolist():
        raise ValueError("Core4 sequence sample order changed")
    baseline = (
        output.loc[output["month_index"].lt(12)]
        .groupby("sample_id", sort=False)["monthly_review_count"]
        .sum()
        .reindex(cohort["sample_id"])
        .to_numpy()
    )
    recent = (
        output.loc[output["month_index"].ge(12)]
        .groupby("sample_id", sort=False)["monthly_review_count"]
        .sum()
        .reindex(cohort["sample_id"])
        .to_numpy()
    )
    if not np.array_equal(baseline, cohort["baseline_review_count"].to_numpy()):
        raise ValueError("Core4 baseline monthly totals differ from source")
    if not np.array_equal(recent, cohort["recent_review_count"].to_numpy()):
        raise ValueError("Core4 recent monthly totals differ from source")
    return output


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    user_json = args.user_json.resolve()
    required = [
        SOURCE_PATH,
        RESTAURANT_REVIEWS_PATH,
        CULINARY_REVIEWS_PATH,
        user_json,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing v05_05 inputs:\n- " + "\n- ".join(missing))
    existing = [path for path in [LIFECYCLE_PATH, SEQUENCE_PATH, METADATA_PATH] if path.exists()]
    if existing and not args.overwrite:
        raise FileExistsError(f"{existing[0]} exists; use --overwrite")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    print("1/4 development cohort만 필터 로드 (selection_year <= 2017)", flush=True)
    cohort = load_development_cohort()
    print("2/4 User 원천 데이터에서 시점 안전 Lifecycle 5개 생성", flush=True)
    lifecycle, lifecycle_diagnostics = build_lifecycle(cohort, user_json)
    print("3/4 음식 관련 리뷰에서 24개월 Core4 시퀀스 생성", flush=True)
    active = build_active_months(cohort)
    sequence = complete_sequence(cohort, active)
    print("4/4 Test 미포함 계약 검증 및 저장", flush=True)
    atomic_parquet(lifecycle, LIFECYCLE_PATH)
    atomic_parquet(sequence, SEQUENCE_PATH)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version": VERSION,
        "status": "development_features_only",
        "samples": len(cohort),
        "selection_year_min": int(cohort["selection_year"].min()),
        "selection_year_max": int(cohort["selection_year"].max()),
        "final_test_rows_loaded": 0,
        "sequence_rows": len(sequence),
        "sequence_length": config["sequence_length"],
        "sequence_channels": config["sequence_channels"],
        "lifecycle_features": config["lifecycle_features"],
        "lifecycle_definitions": {
            "account_age_days": "days from yelping_since to January 1 after selection_year",
            "elite_year_count_prior": "count of Elite years strictly before selection_year",
            "is_elite_selection_year": "whether selection_year appears in Elite history",
            "years_since_last_elite": "selection_year minus latest Elite year at or before selection; -1 when unavailable",
            "recent_elite_streak": "consecutive Elite years ending at selection_year; zero when not Elite in selection_year",
        },
        "monthly_interval_definition": "mean within-calendar-month gap between consecutive culinary reviews; zero for fewer than two reviews",
        "lifecycle_diagnostics": lifecycle_diagnostics,
        "inputs": {
            "modeling_dataset": str(SOURCE_PATH),
            "restaurant_reviews": str(RESTAURANT_REVIEWS_PATH),
            "culinary_reviews": str(CULINARY_REVIEWS_PATH),
            "user_json": str(user_json),
            "user_json_size_bytes": user_json.stat().st_size,
        },
        "artifacts": {
            "lifecycle_path": str(LIFECYCLE_PATH),
            "lifecycle_sha256": sha256(LIFECYCLE_PATH),
            "sequence_path": str(SEQUENCE_PATH),
            "sequence_sha256": sha256(SEQUENCE_PATH),
        },
        "test_policy": config["test_policy"],
        "elapsed_seconds": time.perf_counter() - started,
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"saved development-only features: samples={len(cohort):,}, "
        f"sequence_rows={len(sequence):,}, elapsed={metadata['elapsed_seconds']:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
