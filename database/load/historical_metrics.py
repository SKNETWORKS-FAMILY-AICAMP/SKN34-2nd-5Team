from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


FEATURE_IMPORTANCE_COLUMNS = [
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

FEATURE_GROUP_IMPORTANCE_COLUMNS = [
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


@dataclass
class HistoricalMetricBundle:
    model_version: str
    project_root: Path
    sources: dict[str, Path]
    frames: list[tuple[str, pd.DataFrame]]
    summary: dict[str, Any]


def require_files(paths: dict[str, Path], model_version: str) -> None:
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"필수 {model_version} 비교 리포트 누락:\n- "
            + "\n- ".join(missing)
        )


def require_columns(
    frame: pd.DataFrame,
    columns: set[str],
    source_name: str,
) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(
            f"{source_name}: 필수 컬럼 누락: {', '.join(sorted(missing))}"
        )


def assert_finite(
    frame: pd.DataFrame,
    columns: list[str],
    source_name: str,
    *,
    allow_null: set[str] | None = None,
) -> None:
    nullable_columns = allow_null or set()
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if column not in nullable_columns and values.isna().any():
            raise ValueError(f"{source_name}: {column}에 NULL/비수치 값이 있습니다.")
        finite = values.dropna().to_numpy(dtype=float)
        if not np.isfinite(finite).all():
            raise ValueError(f"{source_name}: {column}에 무한값이 있습니다.")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_contract(
    project_root: Path,
    paths: dict[str, Path],
) -> tuple[dict[str, str], str]:
    manifest = {
        path.relative_to(project_root).as_posix(): sha256(path)
        for path in sorted(paths.values())
    }
    encoded = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return manifest, hashlib.sha256(encoded).hexdigest()


def model_version_frame(
    *,
    project_root: Path,
    paths: dict[str, Path],
    model_version: str,
    model_name: str,
    model_type: str,
    problem_type: str,
    feature_set: str,
    feature_count: int,
    test_selection_year: int,
    test_target_year: int,
    test_samples: int,
    priority_target_rate: float,
    model_parameters: dict[str, Any],
    decision_thresholds: dict[str, Any],
    test_metrics: dict[str, float],
) -> pd.DataFrame:
    manifest, bundle_sha = source_contract(project_root, paths)
    metadata = {
        "version": model_version,
        "artifact_scope": "trust_center_metrics_only",
        "model_artifact_available": False,
        "source_files": manifest,
        "source_bundle_sha256": bundle_sha,
        "test_metrics": test_metrics,
    }
    return pd.DataFrame(
        [
            {
                "model_version": model_version,
                "model_name": model_name,
                "model_type": model_type,
                "problem_type": problem_type,
                "feature_set": feature_set,
                "feature_count": feature_count,
                "test_selection_year": test_selection_year,
                "test_target_year": test_target_year,
                "test_samples": test_samples,
                "priority_target_rate": priority_target_rate,
                # v02/v03 모델 바이너리는 저장소에 없다. 리포트 해시를
                # 모델 해시로 가장하지 않고 metadata_json에 별도 보존한다.
                "model_sha256": None,
                "python_version": None,
                "sklearn_version": None,
                "pandas_version": None,
                "model_parameters": json.dumps(
                    model_parameters,
                    ensure_ascii=False,
                ),
                "decision_thresholds": json.dumps(
                    decision_thresholds,
                    ensure_ascii=False,
                ),
                "metadata_json": json.dumps(metadata, ensure_ascii=False),
            }
        ]
    )


def v03_source_paths(project_root: Path) -> dict[str, Path]:
    tables = project_root / "reports" / "tables"
    return {
        "validation": tables / "multiclass_validation_results_v03.csv",
        "topk": tables / "multiclass_top_k_performance_v03.csv",
        "confusion": tables / "multiclass_confusion_matrix_v03.csv",
        "feature": tables / "final_feature_importance_v03.csv",
        "feature_group": tables / "final_feature_group_importance_v03.csv",
    }


def load_v03_bundle(project_root: Path) -> HistoricalMetricBundle:
    root = project_root.resolve()
    paths = v03_source_paths(root)
    require_files(paths, "v03")

    validation = pd.read_csv(paths["validation"])
    topk = pd.read_csv(paths["topk"])
    confusion = pd.read_csv(paths["confusion"])
    feature = pd.read_csv(paths["feature"])
    feature_group = pd.read_csv(paths["feature_group"])

    require_columns(
        validation,
        {
            "record_type",
            "split",
            "validation_samples",
            "macro_f1",
            "macro_pr_auc",
            "macro_ovr_roc_auc",
        },
        paths["validation"].name,
    )
    require_columns(
        topk,
        {
            "split",
            "ranking",
            "target_rate",
            "target_users",
            "status_loss_captured",
        },
        paths["topk"].name,
    )
    require_columns(
        confusion,
        {
            "split",
            "decision_policy",
            "actual_state",
            "predicted_state",
            "users",
        },
        paths["confusion"].name,
    )
    require_columns(
        feature,
        {
            "rank",
            "feature",
            "feature_group",
            "feature_group_label",
            "importance_mean",
            "importance_std",
            "importance_share_pct",
        },
        paths["feature"].name,
    )
    require_columns(
        feature_group,
        {
            "rank",
            "feature_group",
            "feature_group_label",
            "feature_count",
            "importance_mean",
            "importance_std",
            "baseline_pr_auc",
        },
        paths["feature_group"].name,
    )

    final_rows = validation.loc[validation["record_type"].eq("final_test")]
    if len(validation) != 9 or len(final_rows) != 1:
        raise ValueError("v03 검증 결과가 9행/final_test 1행 계약과 다릅니다.")
    final = final_rows.iloc[0]
    test_samples = int(final["validation_samples"])
    if test_samples != 4_157:
        raise ValueError("v03 최종 Test 표본이 4,157명이 아닙니다.")

    top20 = topk.loc[
        topk["split"].eq("final_test")
        & topk["ranking"].eq("unified")
        & np.isclose(topk["target_rate"], 0.20)
    ]
    if len(topk) != 48 or len(top20) != 1:
        raise ValueError("v03 Top-K가 48행/통합 Top 20% 계약과 다릅니다.")
    if int(top20.iloc[0]["target_users"]) != 832:
        raise ValueError("v03 통합 Top 20% 대상이 832명이 아닙니다.")

    policies = set(confusion["decision_policy"].dropna().astype(str))
    if policies != {"threshold"}:
        raise ValueError(
            "v03 혼동행렬에 threshold 외 정책이 있어 기존 PK로 구분할 수 없습니다."
        )
    final_confusion = confusion.loc[confusion["split"].eq("final_test")]
    if (
        len(confusion) != 63
        or len(final_confusion) != 9
        or int(final_confusion["users"].sum()) != test_samples
    ):
        raise ValueError("v03 혼동행렬이 63행/final_test 4,157명 계약과 다릅니다.")

    baseline_pr_auc = float(final["macro_pr_auc"])
    if len(feature) != 43 or feature["feature"].nunique() != 43:
        raise ValueError("v03 개별 피처 중요도가 43개 고유 피처가 아닙니다.")
    if (
        len(feature_group) != 3
        or int(feature_group["feature_count"].sum()) != 43
        or not np.allclose(feature_group["baseline_pr_auc"], baseline_pr_auc)
    ):
        raise ValueError("v03 그룹 중요도가 3개 그룹/Core 43개 계약과 다릅니다.")
    assert_finite(
        feature,
        [
            "importance_mean",
            "importance_std",
            "importance_share_pct",
        ],
        paths["feature"].name,
    )
    assert_finite(
        feature_group,
        ["importance_mean", "importance_std", "baseline_pr_auc"],
        paths["feature_group"].name,
        allow_null={"importance_std"},
    )

    validation_db = validation.copy()
    validation_db.insert(0, "model_version", "v03")

    topk_db = topk.copy()
    topk_db.insert(0, "model_version", "v03")

    confusion_db = confusion.drop(columns=["decision_policy"]).copy()
    confusion_db.insert(0, "model_version", "v03")

    feature_db = feature.rename(columns={"rank": "rank_no"}).copy()
    feature_db["model_version"] = "v03"
    feature_db["split"] = "final_test"
    feature_db["baseline_pr_auc"] = baseline_pr_auc
    feature_db["metric"] = "macro_pr_auc"
    feature_db["method"] = "single_feature_permutation"
    feature_db["repeats"] = 20
    feature_db = feature_db[FEATURE_IMPORTANCE_COLUMNS]

    feature_group_db = feature_group.rename(columns={"rank": "rank_no"}).copy()
    feature_group_db["model_version"] = "v03"
    feature_group_db["split"] = "final_test"
    feature_group_db["metric"] = "macro_pr_auc"
    feature_group_db["method"] = "group_ablation_retrain"
    feature_group_db["repeats"] = 1
    feature_group_db = feature_group_db[FEATURE_GROUP_IMPORTANCE_COLUMNS]

    model_versions = model_version_frame(
        project_root=root,
        paths=paths,
        model_version="v03",
        model_name="Core Logistic Multiclass",
        model_type="LogisticRegression",
        problem_type="multiclass_classification",
        feature_set="activity+interval+business",
        feature_count=43,
        test_selection_year=2017,
        test_target_year=2019,
        test_samples=test_samples,
        priority_target_rate=0.20,
        model_parameters={
            "penalty": "l1",
            "C": 0.1,
            "class_weight": "balanced",
        },
        decision_thresholds={
            "weakened_score": 0.36,
            "stopped_score": 0.45,
        },
        test_metrics={
            "macro_f1": float(final["macro_f1"]),
            "macro_pr_auc": baseline_pr_auc,
            "macro_ovr_roc_auc": float(final["macro_ovr_roc_auc"]),
        },
    )

    summary = {
        "model_version": "v03",
        "artifact_scope": "trust_center_metrics_only",
        "model_artifact_available": False,
        "test_samples": test_samples,
        "validation_metric_rows": len(validation_db),
        "topk_rows": len(topk_db),
        "confusion_rows": len(confusion_db),
        "feature_importance_rows": len(feature_db),
        "feature_group_importance_rows": len(feature_group_db),
    }
    return HistoricalMetricBundle(
        model_version="v03",
        project_root=root,
        sources=paths,
        frames=[
            ("model_versions", model_versions),
            ("model_validation_metrics", validation_db),
            ("model_topk_metrics", topk_db),
            ("model_confusion_matrix", confusion_db),
            ("feature_importance", feature_db),
            ("feature_group_importance", feature_group_db),
        ],
        summary=summary,
    )


def v02_source_paths(project_root: Path) -> dict[str, Path]:
    tables = project_root / "reports" / "tables"
    return {
        "baseline_validation": tables / "baseline_validation_results_v02.csv",
        "focused_validation": tables / "focused_feature_validation_results_v02.csv",
        "validation_test": tables / "validation_test_comparison_v02.csv",
        "final_test": tables / "final_test_results_v02.csv",
        "validation_topk": tables / "validation_top_k_performance_v02.csv",
        "final_test_topk": tables / "final_test_top_k_performance_v02.csv",
        "feature": tables / "final_feature_importance_v02.csv",
        "feature_group": tables / "final_feature_group_importance_v02.csv",
    }


def binary_validation_row(
    source: pd.Series,
    *,
    split: str,
    selection_year: int,
    target_year: int,
    train_selection_years: str | None,
    train_samples: int | None,
    evaluation_policy: str,
) -> dict[str, Any]:
    validation_samples = int(
        source["true_negative"]
        + source["false_positive"]
        + source["false_negative"]
        + source["true_positive"]
    )
    return {
        "model_version": "v02",
        "split": split,
        "selection_year": selection_year,
        "target_year": target_year,
        "train_selection_years": train_selection_years,
        "train_samples": train_samples,
        "validation_samples": validation_samples,
        "evaluation_policy": evaluation_policy,
        "threshold": float(source["threshold"]),
        "accuracy": float(source["accuracy"]),
        "precision_score": float(source["precision"]),
        "recall_score": float(source["recall"]),
        "f1": float(source["f1"]),
        "roc_auc": float(source["roc_auc"]),
        "pr_auc": float(source["pr_auc"]),
        "true_negative": int(source["true_negative"]),
        "false_positive": int(source["false_positive"]),
        "false_negative": int(source["false_negative"]),
        "true_positive": int(source["true_positive"]),
        "predicted_positive_rate": float(source["predicted_churn_rate"]),
    }


def binary_confusion_rows(
    validation: pd.DataFrame,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    mappings = [
        ("active", "active", "true_negative"),
        ("active", "stopped", "false_positive"),
        ("stopped", "active", "false_negative"),
        ("stopped", "stopped", "true_positive"),
    ]
    for row in validation.to_dict("records"):
        for actual_state, predicted_state, source_column in mappings:
            records.append(
                {
                    "model_version": "v02",
                    "split": row["split"],
                    "actual_state": actual_state,
                    "predicted_state": predicted_state,
                    "users": int(row[source_column]),
                }
            )
    return pd.DataFrame(records)


def load_v02_bundle(project_root: Path) -> HistoricalMetricBundle:
    root = project_root.resolve()
    paths = v02_source_paths(root)
    require_files(paths, "v02")

    baseline = pd.read_csv(paths["baseline_validation"])
    focused = pd.read_csv(paths["focused_validation"])
    comparison = pd.read_csv(paths["validation_test"])
    final_test = pd.read_csv(paths["final_test"])
    validation_topk = pd.read_csv(paths["validation_topk"])
    final_topk = pd.read_csv(paths["final_test_topk"])
    feature = pd.read_csv(paths["feature"])
    feature_group = pd.read_csv(paths["feature_group"])

    metric_columns = {
        "threshold",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "pr_auc",
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
        "predicted_churn_rate",
    }
    require_columns(
        focused,
        {"feature_set", "feature_count", *metric_columns},
        paths["focused_validation"].name,
    )
    require_columns(
        final_test,
        {
            "model",
            "feature_set",
            "feature_count",
            "train_selection_years",
            "test_selection_year",
            "test_target_year",
            "evaluation_policy",
            *metric_columns,
        },
        paths["final_test"].name,
    )
    require_columns(
        comparison,
        {
            "dataset",
            "selection_year",
            "target_year",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "pr_auc",
        },
        paths["validation_test"].name,
    )

    selected_validation = focused.loc[focused["feature_set"].eq("01_core")]
    if len(selected_validation) != 1:
        raise ValueError("v02 검증 결과에서 01_core 행이 정확히 1개가 아닙니다.")
    if len(final_test) != 1:
        raise ValueError("v02 최종 Test 결과가 정확히 1행이 아닙니다.")
    validation_source = selected_validation.iloc[0]
    final_source = final_test.iloc[0]
    if int(validation_source["feature_count"]) != 43:
        raise ValueError("v02 검증 Core 피처 수가 43개가 아닙니다.")
    if int(final_source["feature_count"]) != 43:
        raise ValueError("v02 최종 Test Core 피처 수가 43개가 아닙니다.")

    for label, source, comparison_label in [
        ("Validation", validation_source, "Validation"),
        ("Test", final_source, "Test"),
    ]:
        compared = comparison.loc[comparison["dataset"].eq(comparison_label)]
        if len(compared) != 1:
            raise ValueError(f"v02 {label} 비교 행이 정확히 1개가 아닙니다.")
        compared_row = compared.iloc[0]
        for metric in ["precision", "recall", "f1", "roc_auc", "pr_auc"]:
            if not np.isclose(float(source[metric]), float(compared_row[metric])):
                raise ValueError(f"v02 {label} {metric} 값이 리포트 간 다릅니다.")

    baseline_hgb = baseline.loc[
        baseline["experiment"].eq("A_all_years")
        & baseline["model"].eq("HistGradientBoosting")
    ]
    if len(baseline_hgb) != 1:
        raise ValueError("v02 기본 HGB의 학습 표본 계약을 확인할 수 없습니다.")
    validation_train_samples = int(baseline_hgb.iloc[0]["train_samples"])

    binary_validation = pd.DataFrame(
        [
            binary_validation_row(
                validation_source,
                split="validation",
                selection_year=2016,
                target_year=2018,
                train_selection_years=None,
                train_samples=validation_train_samples,
                evaluation_policy="standard_threshold_reference",
            ),
            binary_validation_row(
                final_source,
                split="final_test",
                selection_year=int(final_source["test_selection_year"]),
                target_year=int(final_source["test_target_year"]),
                train_selection_years=str(final_source["train_selection_years"]),
                train_samples=None,
                evaluation_policy=str(final_source["evaluation_policy"]),
            ),
        ]
    )
    test_samples = int(
        binary_validation.loc[
            binary_validation["split"].eq("final_test"),
            "validation_samples",
        ].iloc[0]
    )
    if test_samples != 4_157:
        raise ValueError("v02 최종 Test 표본이 4,157명이 아닙니다.")

    topk_columns = {
        "target_rate_pct",
        "target_users",
        "captured_churn_users",
        "precision_at_k",
        "recall_at_k",
        "lift_at_k",
        "minimum_risk_score",
    }
    require_columns(validation_topk, topk_columns, paths["validation_topk"].name)
    require_columns(final_topk, topk_columns, paths["final_test_topk"].name)
    if len(validation_topk) != 8 or len(final_topk) != 8:
        raise ValueError("v02 Validation/Test Top-K가 각각 8행이 아닙니다.")
    topk = pd.concat(
        [
            validation_topk.assign(split="validation"),
            final_topk.assign(split="final_test"),
        ],
        ignore_index=True,
    )
    topk.insert(0, "model_version", "v02")
    topk["target_rate"] = topk.pop("target_rate_pct") / 100
    topk = topk[
        [
            "model_version",
            "split",
            "target_rate",
            "target_users",
            "captured_churn_users",
            "precision_at_k",
            "recall_at_k",
            "lift_at_k",
            "minimum_risk_score",
        ]
    ]
    final_top20 = topk.loc[
        topk["split"].eq("final_test")
        & np.isclose(topk["target_rate"], 0.20)
    ]
    if len(final_top20) != 1 or int(final_top20.iloc[0]["target_users"]) != 832:
        raise ValueError("v02 최종 Test Top 20% 대상이 832명이 아닙니다.")

    confusion = binary_confusion_rows(binary_validation)
    if (
        len(confusion) != 8
        or int(
            confusion.loc[
                confusion["split"].eq("final_test"),
                "users",
            ].sum()
        )
        != test_samples
    ):
        raise ValueError("v02 이진 혼동행렬 변환 결과가 계약과 다릅니다.")

    require_columns(
        feature,
        {
            "rank",
            "feature",
            "feature_group",
            "feature_group_label",
            "importance_mean",
            "importance_std",
            "importance_share_pct",
        },
        paths["feature"].name,
    )
    require_columns(
        feature_group,
        {
            "rank",
            "feature_group",
            "feature_group_label",
            "feature_count",
            "importance_mean",
            "importance_std",
            "baseline_pr_auc",
        },
        paths["feature_group"].name,
    )
    baseline_pr_auc = float(final_source["pr_auc"])
    if len(feature) != 43 or feature["feature"].nunique() != 43:
        raise ValueError("v02 개별 피처 중요도가 43개 고유 피처가 아닙니다.")
    if (
        len(feature_group) != 3
        or int(feature_group["feature_count"].sum()) != 43
        or not np.allclose(feature_group["baseline_pr_auc"], baseline_pr_auc)
    ):
        raise ValueError("v02 그룹 중요도가 3개 그룹/Core 43개 계약과 다릅니다.")
    assert_finite(
        feature,
        [
            "importance_mean",
            "importance_std",
            "importance_share_pct",
        ],
        paths["feature"].name,
    )
    assert_finite(
        feature_group,
        ["importance_mean", "importance_std", "baseline_pr_auc"],
        paths["feature_group"].name,
    )

    feature_db = feature.rename(columns={"rank": "rank_no"}).copy()
    feature_db["model_version"] = "v02"
    feature_db["split"] = "final_test"
    feature_db["baseline_pr_auc"] = baseline_pr_auc
    feature_db["metric"] = "pr_auc"
    feature_db["method"] = "single_feature_permutation"
    feature_db["repeats"] = 10
    feature_db = feature_db[FEATURE_IMPORTANCE_COLUMNS]

    feature_group_db = feature_group.rename(columns={"rank": "rank_no"}).copy()
    feature_group_db["model_version"] = "v02"
    feature_group_db["split"] = "final_test"
    feature_group_db["metric"] = "pr_auc"
    feature_group_db["method"] = "joint_group_permutation"
    feature_group_db["repeats"] = 10
    feature_group_db = feature_group_db[FEATURE_GROUP_IMPORTANCE_COLUMNS]

    model_versions = model_version_frame(
        project_root=root,
        paths=paths,
        model_version="v02",
        model_name=str(final_source["model"]),
        model_type="HistGradientBoostingClassifier",
        problem_type="binary_classification",
        feature_set=str(final_source["feature_set"]),
        feature_count=43,
        test_selection_year=int(final_source["test_selection_year"]),
        test_target_year=int(final_source["test_target_year"]),
        test_samples=test_samples,
        priority_target_rate=0.20,
        model_parameters={
            "source": "DEC-005",
            "selected_by": "validation_pr_auc",
        },
        decision_thresholds={
            "standard_threshold": float(final_source["threshold"]),
        },
        test_metrics={
            "f1": float(final_source["f1"]),
            "pr_auc": baseline_pr_auc,
            "roc_auc": float(final_source["roc_auc"]),
        },
    )

    summary = {
        "model_version": "v02",
        "artifact_scope": "trust_center_metrics_only",
        "model_artifact_available": False,
        "test_samples": test_samples,
        "binary_validation_metric_rows": len(binary_validation),
        "binary_topk_rows": len(topk),
        "confusion_rows": len(confusion),
        "feature_importance_rows": len(feature_db),
        "feature_group_importance_rows": len(feature_group_db),
    }
    return HistoricalMetricBundle(
        model_version="v02",
        project_root=root,
        sources=paths,
        frames=[
            ("model_versions", model_versions),
            ("model_binary_validation_metrics", binary_validation),
            ("model_binary_topk_metrics", topk),
            ("model_confusion_matrix", confusion),
            ("feature_importance", feature_db),
            ("feature_group_importance", feature_group_db),
        ],
        summary=summary,
    )


def parse_args(model_version: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            f"Yelp 리텐션 {model_version} Trust Center 비교 리포트를 "
            "MySQL에 적재합니다."
        )
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="SKN34-2nd-5Team 프로젝트 루트",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="리포트 계약만 검증하고 DB에는 연결하지 않습니다.",
    )
    parser.add_argument(
        "--apply-schema",
        action="store_true",
        help="적재 전에 database/ddl/001~010 SQL을 순서대로 실행합니다.",
    )
    parser.add_argument(
        "--confirm-database",
        help="실제 연결된 DB 이름과 정확히 일치해야 적재를 진행합니다.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1_000,
        help="MySQL 배치 적재 행 수",
    )
    return parser.parse_args()


def assert_clean_target(connection, bundle: HistoricalMetricBundle) -> None:
    occupied: dict[str, int] = {}
    for table_name, _ in bundle.frames:
        count = int(
            connection.exec_driver_sql(
                f"SELECT COUNT(*) FROM {table_name} WHERE model_version = %s",
                (bundle.model_version,),
            ).scalar_one()
        )
        if count:
            occupied[table_name] = count
    if occupied:
        raise RuntimeError(
            f"이미 {bundle.model_version} 비교 데이터가 있어 안전상 중단합니다. "
            "자동 삭제/덮어쓰기는 하지 않습니다: "
            + json.dumps(occupied, ensure_ascii=False)
        )


def load_mysql(
    bundle: HistoricalMetricBundle,
    args: argparse.Namespace,
) -> None:
    if not args.confirm_database:
        raise RuntimeError(
            "오적재 방지를 위해 --confirm-database에 대상 DB 이름을 입력해야 합니다."
        )

    from database.load.load_v04 import (
        apply_schema,
        create_engine_from_env,
        database_name,
        nullable,
    )

    engine = create_engine_from_env(bundle.project_root)
    try:
        if args.apply_schema:
            with engine.begin() as connection:
                actual_database = database_name(connection)
                if actual_database != args.confirm_database:
                    raise RuntimeError(
                        f"연결 DB({actual_database})와 확인값"
                        f"({args.confirm_database})이 다릅니다."
                    )
                apply_schema(connection, bundle.project_root)

        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"연결 DB({actual_database})와 확인값"
                    f"({args.confirm_database})이 다릅니다."
                )
            assert_clean_target(connection, bundle)
            for table_name, frame in bundle.frames:
                nullable(frame).to_sql(
                    table_name,
                    con=connection,
                    if_exists="append",
                    index=False,
                    chunksize=args.chunk_size,
                    method="multi",
                )
                print(f"loaded: {table_name} ({len(frame):,} rows)")
    finally:
        engine.dispose()


def run_cli(model_version: str) -> int:
    args = parse_args(model_version)
    try:
        if model_version == "v03":
            bundle = load_v03_bundle(args.project_root)
        elif model_version == "v02":
            bundle = load_v02_bundle(args.project_root)
        else:
            raise ValueError(f"지원하지 않는 비교 버전: {model_version}")
        print(json.dumps(bundle.summary, ensure_ascii=False, indent=2))
        if args.dry_run:
            print("dry-run complete: DB 변경 없음")
            return 0
        load_mysql(bundle, args)
        print(f"{model_version} Trust Center metrics MySQL load complete")
        return 0
    except Exception as error:
        print(f"ERROR: {error}")
        return 1
