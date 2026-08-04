"""Load validated v05 XGBoost comparison metrics into MySQL.

This loader intentionally writes only model/validation tables used by Trust Center.
It does not replace the operational ``v05_05_dl`` reviewer predictions and it never
deserializes the joblib model. The binary is used only for its SHA256 contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.load.load_v04 import (  # noqa: E402
    apply_schema,
    create_engine_from_env,
    database_name,
    nullable,
)


MODEL_VERSION = "v05_ml_xgb"
SOURCE_VERSION = "v05"
MODEL_NAME = "XGBoost Multiclass v05 (Trust comparison)"
MODEL_TYPE = "xgboost.XGBClassifier"
EXPECTED_VALIDATION_ROWS = 9
EXPECTED_TOPK_ROWS = 48
EXPECTED_CONFUSION_ROWS = 63
EXPECTED_FEATURE_COUNT = 45
EXPECTED_TEST_SAMPLES = 6_533
EXPECTED_TOP20_USERS = 1_307

VALIDATION_COLUMNS = [
    "model_version",
    "record_type",
    "split",
    "train_selection_years",
    "validation_selection_year",
    "train_samples",
    "validation_samples",
    "accuracy",
    "balanced_accuracy",
    "macro_precision",
    "macro_recall",
    "macro_f1",
    "weighted_f1",
    "macro_pr_auc",
    "macro_ovr_roc_auc",
    "retained_precision",
    "retained_recall",
    "retained_f1",
    "retained_support",
    "retained_pr_auc",
    "retained_roc_auc",
    "weakened_precision",
    "weakened_recall",
    "weakened_f1",
    "weakened_support",
    "weakened_pr_auc",
    "weakened_roc_auc",
    "stopped_precision",
    "stopped_recall",
    "stopped_f1",
    "stopped_support",
    "stopped_pr_auc",
    "stopped_roc_auc",
]

TOPK_COLUMNS = [
    "model_version",
    "split",
    "ranking",
    "target_rate",
    "target_users",
    "status_loss_captured",
    "status_loss_precision",
    "status_loss_recall",
    "status_loss_lift",
    "stopped_captured",
    "stopped_recall",
    "weakened_captured",
    "weakened_recall",
]

CONFUSION_COLUMNS = [
    "model_version",
    "split",
    "actual_state",
    "predicted_state",
    "users",
]

FEATURE_COLUMNS = [
    "model_version",
    "split",
    "feature",
    "rank_no",
    "feature_group",
    "feature_group_label",
    "importance_mean",
    "importance_std",
    "importance_share_pct",
    "baseline_pr_auc",
    "metric",
    "method",
    "repeats",
]

GROUP_COLUMNS = [
    "model_version",
    "split",
    "feature_group",
    "feature_count",
    "rank_no",
    "feature_group_label",
    "importance_mean",
    "importance_std",
    "baseline_pr_auc",
    "metric",
    "method",
    "repeats",
]


@dataclass(frozen=True)
class SourcePaths:
    root: Path
    metadata: Path
    model: Path
    validation: Path
    topk: Path
    confusion: Path
    feature_importance: Path
    candidates: Path
    performance_report: Path


@dataclass
class SourceBundle:
    paths: SourcePaths
    metadata: dict[str, Any]
    model_sha256: str
    selected_candidate: dict[str, Any]
    validation: pd.DataFrame
    topk: pd.DataFrame
    confusion: pd.DataFrame
    feature_importance: pd.DataFrame
    feature_group_importance: pd.DataFrame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load v05 XGBoost metrics as a Trust Center comparison model."
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        required=True,
        help="Directory containing the nine xgboost_*_v05 artifacts.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="SKN34-2nd-5Team project root.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate source contracts without connecting to MySQL.",
    )
    parser.add_argument(
        "--apply-schema",
        action="store_true",
        help="Apply database/ddl before loading.",
    )
    parser.add_argument(
        "--confirm-database",
        help="Must exactly match the connected database name.",
    )
    parser.add_argument("--chunk-size", type=int, default=1_000)
    return parser.parse_args()


def source_paths(root: Path) -> SourcePaths:
    root = root.resolve()
    return SourcePaths(
        root=root,
        metadata=root / "xgboost_multiclass_metadata_v05.json",
        model=root / "xgboost_final_core_multiclass_v05.joblib",
        validation=root / "xgboost_multiclass_validation_results_v05.csv",
        topk=root / "xgboost_multiclass_top_k_performance_v05.csv",
        confusion=root / "xgboost_multiclass_confusion_matrix_v05.csv",
        feature_importance=root / "xgboost_feature_importance_v05.csv",
        candidates=root / "xgboost_multiclass_model_candidates_v05.csv",
        performance_report=root / "xgboost_multiclass_model_performance_v05.md",
    )


def require_files(paths: SourcePaths) -> None:
    missing = [
        str(path)
        for path in [
            paths.metadata,
            paths.model,
            paths.validation,
            paths.topk,
            paths.confusion,
            paths.feature_importance,
            paths.candidates,
            paths.performance_report,
        ]
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError("Required v05 XGBoost artifacts missing:\n- " + "\n- ".join(missing))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_json(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def assert_columns(frame: pd.DataFrame, required: list[str], name: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{name}: required columns missing: {missing}")


def assert_close(actual: Any, expected: Any, name: str) -> None:
    if not np.isclose(float(actual), float(expected), rtol=1e-9, atol=1e-12):
        raise ValueError(f"{name}: expected {expected}, got {actual}")


def derive_feature_group_importance(feature_importance: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (model_version, split, group, label), part in feature_importance.groupby(
        ["model_version", "split", "feature_group", "feature_group_label"],
        sort=False,
    ):
        baselines = part["baseline_pr_auc"].unique()
        metrics = part["metric"].unique()
        repeats = part["repeats"].unique()
        if len(baselines) != 1 or len(metrics) != 1 or len(repeats) != 1:
            raise ValueError(f"feature_importance: inconsistent metadata in group {group}")
        rows.append(
            {
                "model_version": model_version,
                "split": split,
                "feature_group": group,
                "feature_count": int(len(part)),
                "feature_group_label": label,
                "importance_mean": float(part["importance_mean"].sum()),
                "importance_std": float(np.sqrt(np.square(part["importance_std"]).sum())),
                "baseline_pr_auc": float(baselines[0]),
                "metric": str(metrics[0]),
                "method": "sum_single_feature_permutation",
                "repeats": int(repeats[0]),
            }
        )
    result = pd.DataFrame(rows).sort_values(
        ["importance_mean", "feature_group"], ascending=[False, True]
    )
    result["rank_no"] = np.arange(1, len(result) + 1)
    return result[GROUP_COLUMNS].reset_index(drop=True)


def load_and_validate(paths: SourcePaths) -> SourceBundle:
    require_files(paths)
    metadata = json.loads(paths.metadata.read_text(encoding="utf-8"))
    if metadata.get("version") != SOURCE_VERSION:
        raise ValueError(f"metadata version must be {SOURCE_VERSION}")
    if int(metadata.get("feature_count", 0)) != EXPECTED_FEATURE_COUNT:
        raise ValueError("metadata feature_count must be 45")
    feature_names = list(metadata.get("feature_columns", []))
    if len(feature_names) != EXPECTED_FEATURE_COUNT or len(set(feature_names)) != EXPECTED_FEATURE_COUNT:
        raise ValueError("metadata must contain 45 unique feature_columns")
    if int(metadata.get("test_samples", 0)) != EXPECTED_TEST_SAMPLES:
        raise ValueError("metadata test_samples must be 6533")

    model_hash = sha256(paths.model)
    if model_hash != metadata.get("model_sha256"):
        raise ValueError("joblib SHA256 does not match metadata")

    candidates = pd.read_csv(paths.candidates)
    selected = candidates.loc[candidates["selected"].astype(str).str.lower() == "true"]
    if len(selected) != 1:
        raise ValueError("model candidates must contain exactly one selected row")
    selected_candidate = selected.iloc[0].to_dict()

    validation = pd.read_csv(paths.validation)
    assert_columns(validation, VALIDATION_COLUMNS[1:], "validation")
    if len(validation) != EXPECTED_VALIDATION_ROWS:
        raise ValueError(f"validation row count must be {EXPECTED_VALIDATION_ROWS}")
    final_test = validation.loc[validation["record_type"] == "final_test"]
    if len(final_test) != 1:
        raise ValueError("validation must contain exactly one final_test row")
    final_row = final_test.iloc[0]
    if int(final_row["validation_samples"]) != EXPECTED_TEST_SAMPLES:
        raise ValueError("final_test validation_samples must be 6533")
    for metric, expected in metadata["test_metrics"].items():
        assert_close(final_row[metric], expected, f"final_test {metric}")
    validation = validation.copy()
    validation.insert(0, "model_version", MODEL_VERSION)
    validation.loc[validation["record_type"] == "final_test", "split"] = "final_test"
    validation = validation[VALIDATION_COLUMNS]

    topk = pd.read_csv(paths.topk)
    assert_columns(topk, TOPK_COLUMNS[1:], "topk")
    if len(topk) != EXPECTED_TOPK_ROWS:
        raise ValueError(f"topk row count must be {EXPECTED_TOPK_ROWS}")
    top20 = topk.loc[
        (topk["split"] == "final_test")
        & (topk["ranking"] == "unified")
        & np.isclose(topk["target_rate"], 0.20)
    ]
    if len(top20) != 1 or int(top20.iloc[0]["target_users"]) != EXPECTED_TOP20_USERS:
        raise ValueError("final_test unified Top 20% must contain 1307 users")
    for metric, expected in metadata["top20_policy"].items():
        assert_close(top20.iloc[0][metric], expected, f"top20 {metric}")
    topk = topk.copy()
    topk.insert(0, "model_version", MODEL_VERSION)
    topk = topk[TOPK_COLUMNS]

    confusion = pd.read_csv(paths.confusion)
    assert_columns(confusion, CONFUSION_COLUMNS[1:], "confusion")
    if len(confusion) != EXPECTED_CONFUSION_ROWS:
        raise ValueError(f"confusion row count must be {EXPECTED_CONFUSION_ROWS}")
    final_confusion = confusion.loc[confusion["split"] == "final_test"]
    if len(final_confusion) != 9 or int(final_confusion["users"].sum()) != EXPECTED_TEST_SAMPLES:
        raise ValueError("final_test confusion matrix must have 9 cells totaling 6533")
    confusion = confusion.copy()
    confusion.insert(0, "model_version", MODEL_VERSION)
    confusion = confusion[CONFUSION_COLUMNS]

    importance = pd.read_csv(paths.feature_importance)
    assert_columns(
        importance,
        [column for column in FEATURE_COLUMNS if column not in {"rank_no", "model_version"}] + ["rank"],
        "feature_importance",
    )
    if len(importance) != EXPECTED_FEATURE_COUNT or not importance["feature"].is_unique:
        raise ValueError("feature_importance must contain 45 unique features")
    if set(importance["feature"]) != set(feature_names):
        raise ValueError("feature_importance feature set does not match metadata")
    source_splits = sorted(importance["split"].astype(str).unique())
    if source_splits != ["train_pool_data"]:
        raise ValueError(f"unexpected feature importance source split: {source_splits}")
    importance = importance.copy()
    importance["model_version"] = MODEL_VERSION
    importance["split"] = "final_test"
    importance = importance.rename(columns={"rank": "rank_no"})
    importance = importance[FEATURE_COLUMNS]
    group_importance = derive_feature_group_importance(importance)

    return SourceBundle(
        paths=paths,
        metadata=metadata,
        model_sha256=model_hash,
        selected_candidate=selected_candidate,
        validation=validation,
        topk=topk,
        confusion=confusion,
        feature_importance=importance,
        feature_group_importance=group_importance,
    )


def frames_for_mysql(bundle: SourceBundle) -> list[tuple[str, pd.DataFrame]]:
    metadata = sanitize_json(bundle.metadata)
    metadata.update(
        {
            "version": MODEL_VERSION,
            "source_version": SOURCE_VERSION,
            "source_model_name": bundle.metadata.get("model_name"),
            "source_model_type": bundle.metadata.get("model_type"),
            "model_name": MODEL_NAME,
            "model_type": MODEL_TYPE,
            "usage": "trust_center_comparison_only",
            "operational_model_unchanged": "v05_05_dl",
            "source_feature_importance_split": "train_pool_data",
            "normalized_feature_importance_split": "final_test",
            "artifact_sha256": {
                "model": bundle.model_sha256,
                "metadata": sha256(bundle.paths.metadata),
                "validation": sha256(bundle.paths.validation),
                "topk": sha256(bundle.paths.topk),
                "confusion": sha256(bundle.paths.confusion),
                "feature_importance": sha256(bundle.paths.feature_importance),
                "candidates": sha256(bundle.paths.candidates),
                "performance_report": sha256(bundle.paths.performance_report),
            },
        }
    )
    thresholds = {
        "weakened_threshold": float(bundle.selected_candidate["weakened_threshold"]),
        "stopped_threshold": float(bundle.selected_candidate["stopped_threshold"]),
    }
    model_versions = pd.DataFrame(
        [
            {
                "model_version": MODEL_VERSION,
                "model_name": MODEL_NAME,
                "model_type": MODEL_TYPE,
                "problem_type": bundle.metadata["problem_type"],
                "feature_set": bundle.metadata["feature_set"],
                "feature_count": int(bundle.metadata["feature_count"]),
                "test_selection_year": int(bundle.metadata["test_selection_year"]),
                "test_target_year": int(bundle.metadata["test_target_year"]),
                "test_samples": int(bundle.metadata["test_samples"]),
                "priority_target_rate": float(bundle.metadata["priority_policy"]["primary_target_rate"]),
                "model_sha256": bundle.model_sha256,
                "python_version": bundle.metadata.get("python_version"),
                "sklearn_version": bundle.metadata.get("sklearn_version"),
                "pandas_version": bundle.metadata.get("pandas_version"),
                "model_parameters": json.dumps(
                    sanitize_json(bundle.metadata.get("model_parameters", {})),
                    ensure_ascii=False,
                    allow_nan=False,
                ),
                "decision_thresholds": json.dumps(thresholds, ensure_ascii=False, allow_nan=False),
                "metadata_json": json.dumps(metadata, ensure_ascii=False, allow_nan=False),
            }
        ]
    )
    return [
        ("model_versions", model_versions),
        ("model_validation_metrics", bundle.validation),
        ("model_topk_metrics", bundle.topk),
        ("model_confusion_matrix", bundle.confusion),
        ("feature_importance", bundle.feature_importance),
        ("feature_group_importance", bundle.feature_group_importance),
    ]


def assert_clean_target(connection) -> None:
    occupied: dict[str, int] = {}
    for table in [
        "model_versions",
        "model_validation_metrics",
        "model_topk_metrics",
        "model_confusion_matrix",
        "feature_importance",
        "feature_group_importance",
    ]:
        count = int(
            connection.exec_driver_sql(
                f"SELECT COUNT(*) FROM {table} WHERE model_version = %s",
                (MODEL_VERSION,),
            ).scalar_one()
        )
        if count:
            occupied[table] = count
    if occupied:
        raise RuntimeError(
            "Target comparison version already exists; refusing to delete or overwrite: "
            + json.dumps(occupied, ensure_ascii=False)
        )


def validate_loaded(connection, expected: list[tuple[str, pd.DataFrame]]) -> None:
    mismatches: dict[str, dict[str, int]] = {}
    for table, frame in expected:
        actual = int(
            connection.exec_driver_sql(
                f"SELECT COUNT(*) FROM {table} WHERE model_version = %s",
                (MODEL_VERSION,),
            ).scalar_one()
        )
        if actual != len(frame):
            mismatches[table] = {"expected": len(frame), "actual": actual}
    if mismatches:
        raise RuntimeError("Post-load row count mismatch: " + json.dumps(mismatches))


def print_summary(bundle: SourceBundle) -> None:
    final_test = bundle.validation.loc[bundle.validation["record_type"] == "final_test"].iloc[0]
    print(f"model_version: {MODEL_VERSION} (comparison only)")
    print(f"joblib_sha256: {bundle.model_sha256}")
    print(f"validation_rows: {len(bundle.validation)}")
    print(f"topk_rows: {len(bundle.topk)}")
    print(f"confusion_rows: {len(bundle.confusion)}")
    print(f"feature_importance_rows: {len(bundle.feature_importance)}")
    print(f"feature_group_importance_rows: {len(bundle.feature_group_importance)}")
    print(f"test_samples: {int(final_test['validation_samples'])}")
    print(f"test_macro_f1: {float(final_test['macro_f1']):.6f}")
    print(f"test_macro_pr_auc: {float(final_test['macro_pr_auc']):.6f}")


def main() -> None:
    args = parse_args()
    bundle = load_and_validate(source_paths(args.artifact_root))
    print_summary(bundle)
    if args.dry_run:
        print("dry-run complete: no database connection or write occurred")
        return
    if not args.confirm_database:
        raise RuntimeError("--confirm-database is required for a database write")

    frames = frames_for_mysql(bundle)
    engine = create_engine_from_env(args.project_root.resolve())
    with engine.begin() as connection:
        actual_database = database_name(connection)
        if actual_database != args.confirm_database:
            raise RuntimeError(
                f"Connected database is {actual_database!r}, not {args.confirm_database!r}"
            )
        if args.apply_schema:
            apply_schema(connection, args.project_root.resolve())
        assert_clean_target(connection)
        for table, frame in frames:
            nullable(frame).to_sql(
                table,
                connection,
                if_exists="append",
                index=False,
                chunksize=args.chunk_size,
                method="multi",
            )
            print(f"loaded {table}: {len(frame)} rows")
        validate_loaded(connection, frames)
    print("load complete")


if __name__ == "__main__":
    main()
