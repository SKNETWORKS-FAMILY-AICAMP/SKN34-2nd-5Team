"""Build deterministic 24-month activity sequences for every v04 sample."""

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
VERSION = "v05_03_dl"
CONFIG_PATH = Path(__file__).with_name("config.json")
V04_DATA_PATH = ROOT / "data" / "processed" / "modeling_dataset_rolling_v04.parquet"
RESTAURANT_REVIEWS_PATH = ROOT / "data" / "interim" / "restaurant_reviews.parquet"
CULINARY_REVIEWS_PATH = (
    ROOT / "data" / "interim" / "additional_culinary_reviews_v02.parquet"
)
OUTPUT_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "monthly_sequence_v04_v05_03_dl.parquet"
)
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
METADATA_PATH = REPORT_DIR / "sequence_build_metadata.json"


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


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def validate_inputs(overwrite: bool) -> dict:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for path in [
        V04_DATA_PATH,
        RESTAURANT_REVIEWS_PATH,
        CULINARY_REVIEWS_PATH,
    ]:
        if not path.is_file():
            raise FileNotFoundError(path)
    if OUTPUT_PATH.exists() and not overwrite:
        raise FileExistsError(f"{OUTPUT_PATH} exists; use --overwrite")
    return config


def build_active_months(
    core: pd.DataFrame,
) -> pd.DataFrame:
    cohort = core[
        ["sample_id", "user_id", "comparison_year", "selection_year"]
    ].copy()
    connection = duckdb.connect()
    try:
        connection.execute("SET threads = 1")
        connection.execute("SET preserve_insertion_order = true")
        connection.register("cohort", cohort)
        sources = (
            f"['{sql_path(RESTAURANT_REVIEWS_PATH)}',"
            f"'{sql_path(CULINARY_REVIEWS_PATH)}']"
        )
        active = connection.execute(
            f"""
            WITH reviews AS (
                SELECT
                    user_id,
                    business_id,
                    YEAR(CAST(date AS TIMESTAMP)) AS review_year,
                    MONTH(CAST(date AS TIMESTAMP)) AS review_month
                FROM read_parquet({sources})
            )
            SELECT
                cohort.sample_id,
                (
                    (reviews.review_year - cohort.comparison_year) * 12
                    + reviews.review_month - 1
                )::SMALLINT AS month_index,
                COUNT(*)::INTEGER AS review_count,
                COUNT(DISTINCT reviews.business_id)::INTEGER
                    AS unique_business_count
            FROM reviews
            INNER JOIN cohort
                ON reviews.user_id = cohort.user_id
               AND reviews.review_year BETWEEN
                   cohort.comparison_year AND cohort.selection_year
            GROUP BY cohort.sample_id, month_index
            ORDER BY cohort.sample_id, month_index
            """
        ).fetchdf()
    finally:
        connection.close()
    if not active["month_index"].between(0, 23).all():
        raise ValueError("Sequence month index escaped 0..23")
    return active


def build_complete_grid(core: pd.DataFrame, active: pd.DataFrame) -> pd.DataFrame:
    samples = core[["sample_id", "comparison_year"]].copy()
    grid = pd.DataFrame(
        {
            "sample_id": np.repeat(samples["sample_id"].to_numpy(), 24),
            "comparison_year": np.repeat(
                samples["comparison_year"].to_numpy(dtype=np.int16),
                24,
            ),
            "month_index": np.tile(np.arange(24, dtype=np.int8), len(samples)),
        }
    )
    grid = grid.merge(
        active,
        on=["sample_id", "month_index"],
        how="left",
        validate="one_to_one",
        sort=False,
    )
    grid[["review_count", "unique_business_count"]] = (
        grid[["review_count", "unique_business_count"]]
        .fillna(0)
        .astype("int32")
    )
    grid["active_flag"] = grid["review_count"].gt(0).astype("int8")
    year = grid["comparison_year"] + grid["month_index"].floordiv(12)
    month = grid["month_index"].mod(12) + 1
    grid["year_month"] = (
        year.astype(str) + "-" + month.astype(str).str.zfill(2)
    )
    return grid[
        [
            "sample_id",
            "month_index",
            "year_month",
            "review_count",
            "unique_business_count",
            "active_flag",
        ]
    ]


def validate_sequence(
    core: pd.DataFrame,
    sequence: pd.DataFrame,
    config: dict,
) -> None:
    expected_rows = config["expected_samples"] * config["sequence_length"]
    if len(sequence) != expected_rows:
        raise ValueError(f"Expected {expected_rows:,} monthly rows")
    if sequence.duplicated(["sample_id", "month_index"]).any():
        raise ValueError("Duplicate sample-month key")
    counts = sequence.groupby("sample_id", sort=False).size()
    if not counts.eq(24).all() or len(counts) != len(core):
        raise ValueError("Every sample must have 24 months")
    if sequence["sample_id"].drop_duplicates().tolist() != core["sample_id"].tolist():
        raise ValueError("Sample order changed")
    if (sequence["unique_business_count"] > sequence["review_count"]).any():
        raise ValueError("Unique businesses cannot exceed reviews")
    if set(sequence["active_flag"].unique()) - {0, 1}:
        raise ValueError("active_flag must be binary")

    baseline = (
        sequence.loc[sequence["month_index"].lt(12)]
        .groupby("sample_id", sort=False)["review_count"]
        .sum()
        .reindex(core["sample_id"])
        .to_numpy()
    )
    recent = (
        sequence.loc[sequence["month_index"].ge(12)]
        .groupby("sample_id", sort=False)["review_count"]
        .sum()
        .reindex(core["sample_id"])
        .to_numpy()
    )
    if not np.array_equal(baseline, core["baseline_review_count"].to_numpy()):
        raise ValueError("Monthly baseline totals differ from Core43")
    if not np.array_equal(recent, core["recent_review_count"].to_numpy()):
        raise ValueError("Monthly recent totals differ from Core43")


def atomic_write(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    config = validate_inputs(args.overwrite)
    core = pd.read_parquet(V04_DATA_PATH)
    if len(core) != config["expected_samples"] or not core["sample_id"].is_unique:
        raise ValueError("Protected v04 sample contract changed")
    print("1/3 v04 표본의 Y-1/Y 월별 활동 집계", flush=True)
    active = build_active_months(core)
    print("2/3 활동 없는 월을 포함한 24개월 그리드 생성", flush=True)
    sequence = build_complete_grid(core, active)
    print("3/3 Core43 연간 합계 교차 검증 및 저장", flush=True)
    validate_sequence(core, sequence, config)
    atomic_write(sequence, OUTPUT_PATH)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version": VERSION,
        "dataset_version": "v04",
        "feature_set": config["feature_set"],
        "samples": len(core),
        "sequence_length": 24,
        "sequence_rows": len(sequence),
        "sequence_channels": config["sequence_channels"],
        "active_month_rows": int(sequence["active_flag"].sum()),
        "time_structure": config["time_structure"],
        "input_sha256": sha256(V04_DATA_PATH),
        "output_sha256": sha256(OUTPUT_PATH),
        "elapsed_seconds": time.perf_counter() - started,
        "notes": [
            "Only comparison-year and selection-year reviews are used.",
            "Months without activity are represented by zeros.",
            "Monthly totals are cross-validated against Core43 annual counts.",
        ],
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"saved={OUTPUT_PATH}, samples={len(core):,}, "
        f"rows={len(sequence):,}, elapsed={metadata['elapsed_seconds']:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
