"""Build validated feature contracts for the v05_04 deep-learning experiments.

The source v05_2 parquet is immutable. This builder keeps all supplied
Core43 and added9 features, derives numerically stable DL alternatives from
the protected 24-month sequence, and records selectable feature sets.
Scaling and imputation are intentionally left to each training fold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal


ROOT = Path(__file__).resolve().parents[2]
VERSION = "v05_04_dl_features"
CONFIG_PATH = Path(__file__).with_name("feature_config.json")
CORE_METADATA_PATH = (
    ROOT / "models" / "final_core_logistic_multiclass_metadata_v04.json"
)
V04_DATA_PATH = (
    ROOT / "data" / "processed" / "modeling_dataset_rolling_v04.parquet"
)
SOURCE_PATH = (
    ROOT / "data" / "processed" / "modeling_dataset_rolling_v05_2.parquet"
)
SEQUENCE_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "monthly_sequence_v04_v05_03_dl.parquet"
)
OUTPUT_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "modeling_dataset_v05_2_dl_features_v05_04.parquet"
)
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
METADATA_PATH = REPORT_DIR / "feature_build_metadata.json"
FEATURE_SETS_PATH = REPORT_DIR / "feature_sets.json"
VALIDATION_PATH = REPORT_DIR / "feature_validation.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the generated v05_04 parquet after all validation passes.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def flatten(groups: dict[str, list[str]]) -> list[str]:
    return [column for columns in groups.values() for column in columns]


def load_contract() -> tuple[dict, list[str], dict[str, list[str]], list[str]]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    core_metadata = json.loads(CORE_METADATA_PATH.read_text(encoding="utf-8"))
    core_features = list(core_metadata["feature_columns"])
    added_groups = {
        name: list(columns)
        for name, columns in config["added_feature_groups"].items()
    }
    added_features = flatten(added_groups)
    if len(core_features) != config["expected_core_features"]:
        raise ValueError("Core feature count differs from the v04 contract")
    if len(added_features) != config["expected_added_features"]:
        raise ValueError("Expected exactly nine supplied additional features")
    if len(set(core_features + added_features)) != len(core_features) + len(
        added_features
    ):
        raise ValueError("Core and added feature contracts overlap")
    return config, core_features, added_groups, added_features


def validate_inputs(overwrite: bool) -> None:
    required = [
        CONFIG_PATH,
        CORE_METADATA_PATH,
        V04_DATA_PATH,
        SOURCE_PATH,
        SEQUENCE_PATH,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n- " + "\n- ".join(missing))
    if OUTPUT_PATH.exists() and not overwrite:
        raise FileExistsError(f"{OUTPUT_PATH} exists; use --overwrite")


def validate_source(
    source: pd.DataFrame,
    protected_v04: pd.DataFrame,
    config: dict,
    core_features: list[str],
    added_features: list[str],
) -> None:
    if len(source) != config["expected_rows"]:
        raise ValueError(f"Expected {config['expected_rows']:,} source rows")
    if len(source.columns) != config["expected_source_columns"]:
        raise ValueError("The supplied v05_2 source must contain 64 columns")
    if not source["sample_id"].is_unique:
        raise ValueError("sample_id must be unique")
    expected_columns = (
        list(config["metadata_columns"]) + core_features + added_features
    )
    if set(source.columns) != set(expected_columns):
        missing = sorted(set(expected_columns) - set(source.columns))
        unexpected = sorted(set(source.columns) - set(expected_columns))
        raise ValueError(
            f"Source schema mismatch; missing={missing}, unexpected={unexpected}"
        )
    if source["sample_id"].tolist() != protected_v04["sample_id"].tolist():
        raise ValueError("v05_2 row order or sample IDs differ from protected v04")
    assert_frame_equal(
        source[protected_v04.columns].reset_index(drop=True),
        protected_v04.reset_index(drop=True),
        check_dtype=False,
        check_exact=True,
    )
    feature_values = source[core_features + added_features].to_numpy(dtype=float)
    if np.isinf(feature_values).any():
        raise ValueError("Infinite source feature values are not allowed")
    if source["selection_year"].min() != 2010 or source["selection_year"].max() != 2018:
        raise ValueError("Selection-year contract changed")
    final_test = source.loc[source["selection_year"].eq(2018)]
    if len(final_test) != 6_533 or not final_test["target_year"].eq(2019).all():
        raise ValueError("Final test time contract changed")


def sequence_matrix(
    source: pd.DataFrame,
    sequence: pd.DataFrame,
    sequence_length: int,
) -> np.ndarray:
    required = {"sample_id", "month_index", "review_count"}
    if not required.issubset(sequence.columns):
        raise ValueError("Monthly sequence columns are missing")
    if sequence.duplicated(["sample_id", "month_index"]).any():
        raise ValueError("Duplicate sample-month sequence key")
    counts = sequence.groupby("sample_id", sort=False).size()
    if len(counts) != len(source) or not counts.eq(sequence_length).all():
        raise ValueError("Every sample must have exactly 24 sequence months")
    matrix = (
        sequence.pivot(index="sample_id", columns="month_index", values="review_count")
        .reindex(source["sample_id"])
        .to_numpy(dtype=np.int32)
    )
    if matrix.shape != (len(source), sequence_length):
        raise ValueError("Unexpected monthly review matrix shape")
    if np.isnan(matrix.astype(float)).any() or (matrix < 0).any():
        raise ValueError("Monthly review counts must be complete and non-negative")
    return matrix


def build_dl_features(source: pd.DataFrame, monthly_reviews: np.ndarray) -> pd.DataFrame:
    previous3 = monthly_reviews[:, 18:21].sum(axis=1).astype(np.int32)
    recent3 = monthly_reviews[:, 21:24].sum(axis=1).astype(np.int32)
    selection_year_reviews = monthly_reviews[:, 12:24]
    active = selection_year_reviews > 0
    has_active = active.any(axis=1)
    last_active_index = np.where(
        has_active,
        np.max(np.where(active, np.arange(12), -1), axis=1),
        -1,
    )
    inactive_streak = np.where(has_active, 11 - last_active_index, 12).astype(
        np.int8
    )
    elite_available = source["years_since_last_elite"].ge(0)

    result = pd.DataFrame(
        {
            "dl_review_count_prev3m": previous3,
            "dl_review_count_recent3m": recent3,
            "dl_review_recent3m_vs_prev3m_smoothed": (
                (recent3.astype(float) + 1.0) / (previous3.astype(float) + 1.0)
            ),
            "dl_review_recent3m_log_ratio": (
                np.log1p(recent3.astype(float))
                - np.log1p(previous3.astype(float))
            ),
            "dl_previous3m_inactive": previous3 == 0,
            "dl_current_inactive_streak": inactive_streak,
            "dl_elite_history_available": elite_available.astype("int8"),
            "dl_years_since_last_elite_observed": source[
                "years_since_last_elite"
            ].where(elite_available),
            "dl_recency_vs_mean_interval_log1p": np.log1p(
                source["recency_vs_mean_interval"].astype(float)
            ),
        },
        index=source.index,
    )
    result["dl_previous3m_inactive"] = result[
        "dl_previous3m_inactive"
    ].astype("int8")
    return result


def reconcile_supplied_monthly_features(
    source: pd.DataFrame,
    monthly_reviews: np.ndarray,
) -> dict[str, int | float]:
    local_inactive3 = (monthly_reviews[:, 21:24] == 0).sum(axis=1)
    local_inactive6 = (monthly_reviews[:, 18:24] == 0).sum(axis=1)
    supplied_inactive3 = source["inactive_month_count_3m"].to_numpy()
    supplied_inactive6 = source["inactive_month_count_6m"].to_numpy()
    match3 = int(np.equal(local_inactive3, supplied_inactive3).sum())
    match6 = int(np.equal(local_inactive6, supplied_inactive6).sum())
    return {
        "rows": len(source),
        "inactive_month_count_3m_exact_matches": match3,
        "inactive_month_count_3m_exact_match_rate": match3 / len(source),
        "inactive_month_count_6m_exact_matches": match6,
        "inactive_month_count_6m_exact_match_rate": match6 / len(source),
    }


def build_feature_sets(
    config: dict,
    core_features: list[str],
    added_groups: dict[str, list[str]],
) -> dict[str, list[str]]:
    tenure = added_groups["tenure"]
    momentum = added_groups["momentum"]
    core52 = core_features + tenure + momentum
    drop8 = set(config["importance_drop8"])
    drop7 = set(config["importance_drop7_keep_decline"])
    light_drop = set(config["lightweight_drop23"])
    derived = list(config["dl_derived_features"])

    stable_supplied = [
        "active_years",
        "review_count_slope_6m",
        "inactive_month_count_6m",
        "inactive_month_count_3m",
        "unique_business_slope_6m",
        "months_since_last_new_business",
    ]
    stable_derived = [
        "dl_review_count_prev3m",
        "dl_review_count_recent3m",
        "dl_review_recent3m_log_ratio",
        "dl_current_inactive_streak",
        "dl_elite_history_available",
        "dl_years_since_last_elite_observed",
        "dl_recency_vs_mean_interval_log1p",
    ]
    feature_sets = {
        "core43": core_features,
        "core45_tenure": core_features + tenure,
        "core50_momentum": core_features + momentum,
        "core52_all_supplied": core52,
        "core44_filtered_drop8": [column for column in core52 if column not in drop8],
        "core45_filtered_keep_decline": [
            column for column in core52 if column not in drop7
        ],
        "core29_lightweight": [
            column for column in core52 if column not in light_drop
        ],
        "core61_all_plus_dl_derived": core52 + derived,
        "core56_dl_stable": core_features + stable_supplied + stable_derived,
    }
    forbidden = set(config["forbidden_model_inputs"])
    all_known = set(core52 + derived)
    for name, columns in feature_sets.items():
        if len(columns) != len(set(columns)):
            raise ValueError(f"Duplicate feature in set {name}")
        if forbidden & set(columns):
            raise ValueError(f"Forbidden model input found in set {name}")
        if set(columns) - all_known:
            raise ValueError(f"Unknown feature found in set {name}")
    expected_counts = {
        "core43": 43,
        "core45_tenure": 45,
        "core50_momentum": 50,
        "core52_all_supplied": 52,
        "core44_filtered_drop8": 44,
        "core45_filtered_keep_decline": 45,
        "core29_lightweight": 29,
        "core61_all_plus_dl_derived": 61,
        "core56_dl_stable": 56,
    }
    actual_counts = {name: len(columns) for name, columns in feature_sets.items()}
    if actual_counts != expected_counts:
        raise ValueError(f"Feature-set counts changed: {actual_counts}")
    return feature_sets


def validate_output(
    output: pd.DataFrame,
    source: pd.DataFrame,
    config: dict,
    feature_sets: dict[str, list[str]],
) -> pd.DataFrame:
    assert_frame_equal(
        output[source.columns],
        source,
        check_dtype=False,
        check_exact=True,
    )
    derived = list(config["dl_derived_features"])
    if len(output.columns) != config["expected_source_columns"] + len(derived):
        raise ValueError("Unexpected v05_04 output column count")
    if set(derived) - set(output.columns):
        raise ValueError("DL-derived feature columns are missing")
    if not output["dl_current_inactive_streak"].between(0, 12).all():
        raise ValueError("Inactive streak escaped 0..12")
    if not output["dl_elite_history_available"].isin([0, 1]).all():
        raise ValueError("Elite availability must be binary")
    observed = output["dl_years_since_last_elite_observed"]
    if observed.dropna().lt(0).any():
        raise ValueError("Observed elite recency cannot be negative")
    if not output["dl_review_recent3m_vs_prev3m_smoothed"].gt(0).all():
        raise ValueError("Smoothed 3-month ratio must be positive")
    union_features = sorted(
        {column for columns in feature_sets.values() for column in columns}
    )
    rows = []
    memberships = {
        feature: [name for name, columns in feature_sets.items() if feature in columns]
        for feature in union_features
    }
    for feature in union_features:
        numeric = pd.to_numeric(output[feature], errors="coerce")
        finite = numeric.dropna().to_numpy(dtype=float)
        rows.append(
            {
                "feature": feature,
                "dtype": str(output[feature].dtype),
                "feature_sets": "|".join(memberships[feature]),
                "missing_count": int(output[feature].isna().sum()),
                "missing_rate": float(output[feature].isna().mean()),
                "infinite_count": int(np.isinf(finite).sum()),
                "minimum": float(numeric.min()) if numeric.notna().any() else np.nan,
                "median": float(numeric.median()) if numeric.notna().any() else np.nan,
                "maximum": float(numeric.max()) if numeric.notna().any() else np.nan,
            }
        )
    validation = pd.DataFrame(rows)
    if validation["infinite_count"].sum() != 0:
        raise ValueError("Infinite feature values found in output")
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
    config, core_features, added_groups, added_features = load_contract()

    print("1/4 validate protected v04 and supplied v05_2 contracts", flush=True)
    protected_v04 = pd.read_parquet(V04_DATA_PATH)
    source = pd.read_parquet(SOURCE_PATH)
    validate_source(
        source,
        protected_v04,
        config,
        core_features,
        added_features,
    )

    print("2/4 derive stable DL features from the 24-month sequence", flush=True)
    sequence = pd.read_parquet(
        SEQUENCE_PATH,
        columns=["sample_id", "month_index", "review_count"],
    )
    monthly_reviews = sequence_matrix(source, sequence, config["sequence_length"])
    reconciliation = reconcile_supplied_monthly_features(source, monthly_reviews)
    if (
        reconciliation["inactive_month_count_3m_exact_matches"] != len(source)
        or reconciliation["inactive_month_count_6m_exact_matches"] != len(source)
    ):
        print(
            "warning: supplied inactive-month features do not exactly match "
            "the protected v05_03 monthly sequence; see build metadata",
            flush=True,
        )
    dl_features = build_dl_features(source, monthly_reviews)
    output = pd.concat([source, dl_features], axis=1)

    print("3/4 build and validate selectable feature-set contracts", flush=True)
    feature_sets = build_feature_sets(config, core_features, added_groups)
    validation = validate_output(output, source, config, feature_sets)

    print("4/4 save generated data and reproducibility metadata", flush=True)
    atomic_write_parquet(output, OUTPUT_PATH)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    validation.to_csv(VALIDATION_PATH, index=False, encoding="utf-8-sig")
    FEATURE_SETS_PATH.write_text(
        json.dumps(
            {
                "version": VERSION,
                "dataset_version": config["dataset_version"],
                "feature_sets": feature_sets,
                "feature_counts": {
                    name: len(columns) for name, columns in feature_sets.items()
                },
                "selection_note": (
                    "Select feature sets with expanding-time pooled OOF only; "
                    "do not use final-test labels or final-test importance."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    raw_ratio = source["review_recent3m_vs_prev3m"]
    metadata = {
        "version": VERSION,
        "dataset_version": config["dataset_version"],
        "rows": len(output),
        "source_columns": len(source.columns),
        "output_columns": len(output.columns),
        "metadata_columns": config["metadata_columns"],
        "core_feature_count": len(core_features),
        "supplied_added_feature_count": len(added_features),
        "dl_derived_feature_count": len(config["dl_derived_features"]),
        "dl_derived_features": config["dl_derived_features"],
        "feature_set_counts": {
            name: len(columns) for name, columns in feature_sets.items()
        },
        "time_structure": (
            "comparison Y-1 and selection Y are model inputs; target Y+1 is label only"
        ),
        "input_sha256": {
            "v04_modeling_dataset": sha256(V04_DATA_PATH),
            "v05_2_modeling_dataset": sha256(SOURCE_PATH),
            "monthly_sequence": sha256(SEQUENCE_PATH),
            "feature_config": sha256(CONFIG_PATH),
        },
        "output_sha256": sha256(OUTPUT_PATH),
        "raw_ratio_diagnostic": {
            "feature": "review_recent3m_vs_prev3m",
            "p95": float(raw_ratio.quantile(0.95)),
            "p99": float(raw_ratio.quantile(0.99)),
            "maximum": float(raw_ratio.max()),
            "dl_alternatives": [
                "dl_review_recent3m_vs_prev3m_smoothed",
                "dl_review_recent3m_log_ratio",
            ],
        },
        "supplied_monthly_feature_reconciliation": reconciliation,
        "notes": [
            "The supplied 64-column parquet is never overwritten.",
            "All protected v04 columns and row order are byte-value equivalent after loading.",
            "No global imputation or scaling is applied; training must fit preprocessing inside each fold.",
            "DL-derived recent-window features use months 18..23 only and never use target-year activity.",
            "The core56_dl_stable set replaces unstable sentinel/ratio inputs with explicit DL alternatives.",
            "Supplied inactive-month features are preserved, but their partial mismatch with the protected monthly sequence must be resolved against the teammate's generation code before final model selection.",
        ],
        "elapsed_seconds": time.perf_counter() - started,
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"saved={OUTPUT_PATH}, rows={len(output):,}, columns={len(output.columns)}, "
        f"feature_sets={len(feature_sets)}, elapsed={metadata['elapsed_seconds']:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
