"""Build selection-year 2018 Test features for the frozen v05_05 model.

This module is deliberately separate from ``build_features.py`` so the
development-only contract remains unchanged. It reads no 2019 target label;
2019 outcomes are accessed only by ``evaluate_test.py`` after predictions
have been created from information available through 2018-12-31.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_05_dl import build_features as base


VERSION = "v05_05_dl"
TEST_SELECTION_YEAR = 2018
TEST_TARGET_YEAR = 2019
EXPECTED_TEST_SAMPLES = 6_533
CONFIG_PATH = Path(__file__).with_name("config.json")
SOURCE_PATH = ROOT / "data" / "processed" / "modeling_dataset_rolling_v05_ml.parquet"
OUTPUT_DIR = ROOT / "data" / "processed" / "experiments"
TEST_LIFECYCLE_PATH = OUTPUT_DIR / "test_lifecycle_features_v05_05.parquet"
TEST_SEQUENCE_PATH = OUTPUT_DIR / "test_monthly_core4_sequence_v05_05.parquet"
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
TEST_METADATA_PATH = REPORT_DIR / "test_feature_build_metadata.json"


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


def load_test_cohort() -> pd.DataFrame:
    # Target columns are intentionally omitted. This stage must only create
    # model inputs available at the end of the selection year.
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
        filters=[("selection_year", "==", TEST_SELECTION_YEAR)],
    )
    cohort = cohort.sort_values("sample_id", kind="stable").reset_index(drop=True)
    if len(cohort) != EXPECTED_TEST_SAMPLES:
        raise ValueError(
            f"Expected {EXPECTED_TEST_SAMPLES:,} Test rows, found {len(cohort):,}"
        )
    if not cohort["sample_id"].is_unique:
        raise ValueError("Test sample_id must be unique")
    if not cohort["user_id"].is_unique:
        raise ValueError("Test user_id must be unique")
    if not cohort["selection_year"].eq(TEST_SELECTION_YEAR).all():
        raise ValueError("Non-Test selection year entered the Test cohort")
    if not cohort["comparison_year"].eq(TEST_SELECTION_YEAR - 1).all():
        raise ValueError("Test comparison year must be 2017")
    return cohort


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    user_json = args.user_json.resolve()
    required = [
        CONFIG_PATH,
        SOURCE_PATH,
        base.RESTAURANT_REVIEWS_PATH,
        base.CULINARY_REVIEWS_PATH,
        user_json,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing v05_05 Test inputs:\n- " + "\n- ".join(missing))

    outputs = [TEST_LIFECYCLE_PATH, TEST_SEQUENCE_PATH, TEST_METADATA_PATH]
    existing = [path for path in outputs if path.exists()]
    if existing and not args.overwrite:
        raise FileExistsError(f"{existing[0]} exists; use --overwrite")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    print("1/4 Test 코호트 로드 (selection_year == 2018)", flush=True)
    cohort = load_test_cohort()
    print("2/4 Test Lifecycle 5개 생성", flush=True)
    lifecycle, lifecycle_diagnostics = base.build_lifecycle(cohort, user_json)
    print("3/4 Test 24개월 Core4 시퀀스 생성", flush=True)
    active = base.build_active_months(cohort)
    sequence = base.complete_sequence(cohort, active)
    print("4/4 Test 입력 계약 검증 및 저장", flush=True)

    if set(lifecycle.columns) != {
        "sample_id",
        "selection_year",
        *config["lifecycle_features"],
    }:
        raise ValueError("Test Lifecycle columns differ from the training contract")
    if len(sequence) != EXPECTED_TEST_SAMPLES * int(config["sequence_length"]):
        raise ValueError("Test sequence row count changed")

    base.atomic_parquet(lifecycle, TEST_LIFECYCLE_PATH)
    base.atomic_parquet(sequence, TEST_SEQUENCE_PATH)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version": VERSION,
        "status": "test_features_complete",
        "samples": len(cohort),
        "comparison_year": TEST_SELECTION_YEAR - 1,
        "selection_year": TEST_SELECTION_YEAR,
        "target_year": TEST_TARGET_YEAR,
        "target_columns_loaded": [],
        "sequence_rows": len(sequence),
        "sequence_length": config["sequence_length"],
        "sequence_channels": config["sequence_channels"],
        "lifecycle_features": config["lifecycle_features"],
        "feature_cutoff": "2018-12-31",
        "lifecycle_diagnostics": lifecycle_diagnostics,
        "inputs": {
            "modeling_dataset": str(SOURCE_PATH),
            "restaurant_reviews": str(base.RESTAURANT_REVIEWS_PATH),
            "culinary_reviews": str(base.CULINARY_REVIEWS_PATH),
            "user_json": str(user_json),
            "user_json_size_bytes": user_json.stat().st_size,
        },
        "artifacts": {
            "test_lifecycle_path": str(TEST_LIFECYCLE_PATH),
            "test_lifecycle_sha256": base.sha256(TEST_LIFECYCLE_PATH),
            "test_sequence_path": str(TEST_SEQUENCE_PATH),
            "test_sequence_sha256": base.sha256(TEST_SEQUENCE_PATH),
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    TEST_METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Test features complete: samples={len(cohort):,}, "
        f"sequence_rows={len(sequence):,}, elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
