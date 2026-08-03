"""Build development-only monthly new/revisited-business signals for v05_05_03."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_05_dl import build_features as base


VERSION = "v05_05_03_dl"
OUTPUT_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "monthly_exploration_sequence_v05_05_03.parquet"
)
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
METADATA_PATH = REPORT_DIR / "exploration_feature_metadata.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_active_months(cohort: pd.DataFrame) -> pd.DataFrame:
    registered = cohort[
        ["sample_id", "user_id", "comparison_year", "selection_year"]
    ]
    sources = (
        f"['{base.sql_path(base.RESTAURANT_REVIEWS_PATH)}',"
        f"'{base.sql_path(base.CULINARY_REVIEWS_PATH)}']"
    )
    connection = duckdb.connect()
    try:
        connection.execute("SET threads = 4")
        connection.register("development_cohort", registered)
        result = connection.execute(
            f"""
            WITH cohort_users AS (
                SELECT DISTINCT user_id FROM development_cohort
            ),
            reviews AS (
                SELECT
                    source.user_id,
                    source.business_id,
                    CAST(source.date AS TIMESTAMP) AS review_ts
                FROM read_parquet({sources}) AS source
                INNER JOIN cohort_users AS users
                    ON source.user_id = users.user_id
            ),
            first_visit AS (
                SELECT
                    user_id,
                    business_id,
                    MIN(review_ts) AS first_review_ts
                FROM reviews
                GROUP BY user_id, business_id
            ),
            matched AS (
                SELECT
                    cohort.sample_id,
                    (
                        (YEAR(reviews.review_ts) - cohort.comparison_year) * 12
                        + MONTH(reviews.review_ts) - 1
                    )::SMALLINT AS month_index,
                    reviews.business_id,
                    reviews.review_ts,
                    first_visit.first_review_ts,
                    DATE_TRUNC('month', reviews.review_ts) AS review_month_start
                FROM reviews
                INNER JOIN first_visit
                    ON reviews.user_id = first_visit.user_id
                   AND reviews.business_id = first_visit.business_id
                INNER JOIN development_cohort AS cohort
                    ON reviews.user_id = cohort.user_id
                   AND YEAR(reviews.review_ts) BETWEEN
                       cohort.comparison_year AND cohort.selection_year
            )
            SELECT
                sample_id,
                month_index,
                COUNT(DISTINCT business_id)::INTEGER AS monthly_unique_business_count,
                COUNT(DISTINCT business_id) FILTER (
                    WHERE DATE_TRUNC('month', first_review_ts) = review_month_start
                )::INTEGER AS monthly_new_business_count,
                COUNT(DISTINCT business_id) FILTER (
                    WHERE first_review_ts < review_month_start
                )::INTEGER AS monthly_revisited_business_count
            FROM matched
            GROUP BY sample_id, month_index
            ORDER BY sample_id, month_index
            """
        ).fetchdf()
    finally:
        connection.close()
    if not result["month_index"].between(0, 23).all():
        raise ValueError("Exploration month index escaped 0..23")
    return result


def complete_grid(cohort: pd.DataFrame, active: pd.DataFrame) -> pd.DataFrame:
    grid = pd.DataFrame(
        {
            "sample_id": np.repeat(cohort["sample_id"].to_numpy(), 24),
            "month_index": np.tile(np.arange(24, dtype=np.int8), len(cohort)),
        }
    )
    output = grid.merge(
        active,
        on=["sample_id", "month_index"],
        how="left",
        validate="one_to_one",
        sort=False,
    )
    count_columns = [
        "monthly_unique_business_count",
        "monthly_new_business_count",
        "monthly_revisited_business_count",
    ]
    output[count_columns] = output[count_columns].fillna(0).astype("int32")
    output["monthly_new_business_rate"] = np.divide(
        output["monthly_new_business_count"],
        output["monthly_unique_business_count"],
        out=np.zeros(len(output), dtype=np.float32),
        where=output["monthly_unique_business_count"].gt(0),
    )
    if len(output) != len(cohort) * 24:
        raise ValueError("Every development sample must have 24 exploration months")
    if output["sample_id"].drop_duplicates().tolist() != cohort["sample_id"].tolist():
        raise ValueError("Exploration sample order changed")
    if (
        output["monthly_new_business_count"]
        > output["monthly_unique_business_count"]
    ).any():
        raise ValueError("New businesses cannot exceed unique businesses")
    return output[
        [
            "sample_id",
            "month_index",
            "monthly_unique_business_count",
            "monthly_new_business_count",
            "monthly_new_business_rate",
            "monthly_revisited_business_count",
        ]
    ]


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    if OUTPUT_PATH.exists() and not args.overwrite:
        raise FileExistsError(f"{OUTPUT_PATH} exists; use --overwrite")
    cohort = base.load_development_cohort()
    if cohort["selection_year"].max() >= 2018:
        raise ValueError("Final Test entered exploration feature generation")
    print("1/3 development culinary review history에서 최초 업체 방문 계산", flush=True)
    active = build_active_months(cohort)
    print("2/3 비활동 월을 포함한 24개월 탐색 시퀀스 생성", flush=True)
    output = complete_grid(cohort, active)
    print("3/3 Test 미포함 계약 검증 및 저장", flush=True)
    base.atomic_parquet(output, OUTPUT_PATH)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version": VERSION,
        "status": "development_features_only",
        "samples": len(cohort),
        "selection_year_min": int(cohort["selection_year"].min()),
        "selection_year_max": int(cohort["selection_year"].max()),
        "final_test_rows_loaded": 0,
        "sequence_rows": len(output),
        "definition": (
            "A business is new in a sample-month when the user's first culinary "
            "review of that business occurs in that calendar month. Future reviews "
            "cannot change the historical first-review timestamp."
        ),
        "output_path": str(OUTPUT_PATH),
        "output_sha256": sha256(OUTPUT_PATH),
        "elapsed_seconds": time.perf_counter() - started,
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"saved={OUTPUT_PATH}, rows={len(output):,}, "
        f"elapsed={metadata['elapsed_seconds']:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
