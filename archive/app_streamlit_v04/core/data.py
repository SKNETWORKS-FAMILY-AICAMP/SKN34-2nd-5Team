from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from core.demo_data import build_demo_data
from core.insights import enrich_profiles


V04_CORE_FILES = {
    "reviewer_profiles": (
        "data/processed/predictions/final_test_retention_profiles_v04.parquet"
    ),
    "model_metadata": "models/final_core_logistic_multiclass_metadata_v04.json",
    "multiclass_validation": "reports/tables/multiclass_validation_results_v04.csv",
    "multiclass_top_k": "reports/tables/multiclass_top_k_performance_v04.csv",
    "multiclass_confusion": "reports/tables/multiclass_confusion_matrix_v04.csv",
}

V04_EXPLAINABILITY_FILES = {
    "feature_importance": "reports/tables/final_feature_importance_v04.csv",
    "group_importance": "reports/tables/final_feature_group_importance_v04.csv",
}

V03_COMPARISON_FILES = {
    "multiclass_validation_v03": (
        "reports/tables/multiclass_validation_results_v03.csv"
    ),
    "multiclass_top_k_v03": (
        "reports/tables/multiclass_top_k_performance_v03.csv"
    ),
    "multiclass_confusion_v03": (
        "reports/tables/multiclass_confusion_matrix_v03.csv"
    ),
    "feature_importance_v03": (
        "reports/tables/final_feature_importance_v03.csv"
    ),
    "group_importance_v03": (
        "reports/tables/final_feature_group_importance_v03.csv"
    ),
}

OPTIONAL_FILE_CANDIDATES = {
    "top_k": ["reports/tables/final_test_top_k_performance_v02.csv"],
    "validation_test": [
        "reports/tables/validation_test_comparison_v02.csv",
        "reports/tables/final_validation_test_comparison_v02.csv",
    ],
    "feature_importance_v02": [
        "reports/tables/final_feature_importance_v02.csv",
    ],
    "group_importance_v02": [
        "reports/tables/final_feature_group_importance_v02.csv",
    ],
    "feature_sets": [
        "reports/tables/feature_group_validation_results_v02.csv",
        "reports/tables/final_feature_set_comparison_v02.csv",
    ],
    "reviewer_monthly_activity": [
        "data/processed/predictions/reviewer_monthly_activity_v01.parquet",
        "data/processed/reviewer_monthly_activity_v01.parquet",
    ],
    "regional_risk": [
        "reports/tables/regional_risk_summary_v01.csv",
        "data/processed/regional_risk_summary_v01.parquet",
    ],
}

VALIDATION_ONLY_COLUMNS = {
    "target_review_count",
    "target_active_months",
    "retention_state",
    "retention_state_label",
    "churn",
    "status_loss",
    "actual_result",
}

OPERATIONAL_ID_COLUMNS = [
    "model_version",
    "sample_id",
    "user_id",
    "comparison_year",
    "selection_year",
    "target_year",
    "prior_activity_available",
    "scope",
]

OPERATIONAL_MODEL_COLUMNS = [
    "retained_score",
    "weakened_score",
    "stopped_score",
    "priority_score",
    "predicted_state",
    "predicted_state_label",
    "model_judgment",
    "priority_rank",
    "priority_top_percent",
    "selected_for_crm",
    "crm_target_label",
    "risk_type",
    "core_signal",
    "recommended_review",
]


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    predictions: Path
    reports_tables: Path
    models: Path


@dataclass
class AppData:
    paths: ProjectPaths
    data_mode: str
    model_version: str = "v04"
    comparison_year: int = 2017
    selection_year: int = 2018
    target_year: int = 2019
    reviewer_profiles: pd.DataFrame = field(default_factory=pd.DataFrame)
    top_k: pd.DataFrame = field(default_factory=pd.DataFrame)
    primary_policy: pd.DataFrame = field(default_factory=pd.DataFrame)
    validation_test: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_importance: pd.DataFrame = field(default_factory=pd.DataFrame)
    group_importance: pd.DataFrame = field(default_factory=pd.DataFrame)
    multiclass_validation_v03: pd.DataFrame = field(default_factory=pd.DataFrame)
    multiclass_top_k_v03: pd.DataFrame = field(default_factory=pd.DataFrame)
    multiclass_confusion_v03: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_importance_v03: pd.DataFrame = field(default_factory=pd.DataFrame)
    group_importance_v03: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_importance_v02: pd.DataFrame = field(default_factory=pd.DataFrame)
    group_importance_v02: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_sets: pd.DataFrame = field(default_factory=pd.DataFrame)
    split_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    reviewer_monthly_activity: pd.DataFrame = field(default_factory=pd.DataFrame)
    regional_risk: pd.DataFrame = field(default_factory=pd.DataFrame)
    model_metadata: dict[str, Any] = field(default_factory=dict)
    risk_policy: dict[str, Any] = field(default_factory=dict)
    retention_distribution: pd.DataFrame = field(default_factory=pd.DataFrame)
    multiclass_validation: pd.DataFrame = field(default_factory=pd.DataFrame)
    multiclass_top_k: pd.DataFrame = field(default_factory=pd.DataFrame)
    multiclass_confusion: pd.DataFrame = field(default_factory=pd.DataFrame)
    warnings: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)


def find_project_root() -> Path:
    override = os.getenv("YELP_PROJECT_ROOT")
    if override:
        path = Path(override).expanduser().resolve()
        if path.exists():
            return path

    module_root = Path(__file__).resolve().parents[2]
    candidates: list[Path] = []
    for origin in [Path.cwd().resolve(), module_root]:
        candidates.extend([origin, *origin.parents])

    for candidate in dict.fromkeys(candidates):
        if (candidate / V04_CORE_FILES["reviewer_profiles"]).exists():
            return candidate
    for candidate in dict.fromkeys(candidates):
        if (candidate / "data" / "processed").exists() and (
            candidate / "reports"
        ).exists():
            return candidate
    return module_root


def project_paths(root: Path) -> ProjectPaths:
    return ProjectPaths(
        root=root,
        predictions=root / "data" / "processed" / "predictions",
        reports_tables=root / "reports" / "tables",
        models=root / "models",
    )


def _first_path(root: Path, candidates: list[str]) -> Path | None:
    for relative in candidates:
        path = root / relative
        if path.exists():
            return path
    return None


@st.cache_data(show_spinner=False)
def _read_table(path_text: str) -> pd.DataFrame:
    path = Path(path_text)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def _read_json(path_text: str) -> dict[str, Any]:
    with Path(path_text).open(encoding="utf-8") as file:
        return json.load(file)


def _numeric(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")


def _normalize_profiles(
    frame: pd.DataFrame,
    *,
    model_version: str = "v04",
) -> pd.DataFrame:
    profile = frame.copy()
    if "priority_score" in profile.columns:
        profile["risk_score"] = profile["priority_score"]
    if "priority_rank" in profile.columns:
        profile["risk_rank"] = profile["priority_rank"]
    if "priority_top_percent" in profile.columns:
        profile["risk_top_percent"] = profile["priority_top_percent"]
    if "selected_for_crm" in profile.columns:
        profile["crm_target"] = profile["selected_for_crm"]

    required = {"user_id", "risk_score"}
    missing = required - set(profile.columns)
    if missing:
        raise ValueError(
            "리뷰어 위험 파일 필수 컬럼 누락: " + ", ".join(sorted(missing))
        )

    _numeric(
        profile,
        [
            "risk_score",
            "risk_rank",
            "risk_top_percent",
            "risk_percentile",
            "crm_target",
            "churn",
            "comparison_year",
            "selection_year",
            "target_year",
            "target_review_count",
            "target_active_months",
            "prior_activity_available",
            "baseline_review_count",
            "recent_review_count",
            "review_count_decline_rate",
            "baseline_active_months",
            "recent_active_months",
            "active_month_decline_rate",
            "baseline_unique_business_count",
            "recent_unique_business_count",
            "unique_business_decline_rate",
            "baseline_recency_days",
            "recent_recency_days",
            "recency_increase_days",
            "baseline_mean_interval_days",
            "recent_mean_interval_days",
            "mean_interval_increase_days",
            "retention_state",
            "predicted_state",
            "retained_score",
            "weakened_score",
            "stopped_score",
            "priority_score",
            "priority_rank",
            "priority_top_percent",
            "selected_for_crm",
        ],
    )
    profile = profile.sort_values("risk_score", ascending=False).reset_index(drop=True)
    total = len(profile)

    if "risk_rank" not in profile.columns:
        profile["risk_rank"] = np.arange(1, total + 1)
    profile["risk_rank"] = profile["risk_rank"].fillna(
        pd.Series(np.arange(1, total + 1), index=profile.index)
    )

    if "risk_top_percent" not in profile.columns:
        profile["risk_top_percent"] = profile["risk_rank"] / total * 100
    elif profile["risk_top_percent"].max(skipna=True) <= 1:
        profile["risk_top_percent"] *= 100

    if "risk_percentile" not in profile.columns:
        profile["risk_percentile"] = 100 - (profile["risk_rank"] - 1) / total * 100
    elif profile["risk_percentile"].max(skipna=True) <= 1:
        profile["risk_percentile"] *= 100

    if "risk_tier" not in profile.columns:
        profile["risk_tier"] = pd.cut(
            profile["risk_top_percent"],
            bins=[-np.inf, 5, 20, 40, np.inf],
            labels=["긴급 관리", "집중 관리", "관찰 대상", "일반"],
        ).astype(str)
    else:
        profile["risk_tier"] = profile["risk_tier"].astype(str)

    if "crm_target" not in profile.columns:
        profile["crm_target"] = profile["risk_top_percent"].le(20).astype("int8")
    else:
        profile["crm_target"] = profile["crm_target"].fillna(0).astype("int8")
    profile["crm_target_label"] = np.where(
        profile["crm_target"].eq(1),
        "통합 상위 20% 검토 대상",
        "일반 모니터링",
    )

    state_labels = {
        0: "파워 지위 유지",
        1: "파워 지위 약화",
        2: "리뷰 활동 중단",
    }
    judgment_labels = {
        0: "유지 우세",
        1: "약화 우세",
        2: "중단 우세",
    }
    if "predicted_state" in profile.columns:
        profile["predicted_state"] = profile["predicted_state"].fillna(0).astype("int8")
        profile["model_judgment"] = profile["predicted_state"].map(judgment_labels)
        if "predicted_state_label" not in profile.columns:
            profile["predicted_state_label"] = profile["predicted_state"].map(
                state_labels
            )
    else:
        profile["predicted_state"] = 0
        profile["predicted_state_label"] = state_labels[0]
        profile["model_judgment"] = judgment_labels[0]

    if "retention_state" in profile.columns:
        profile["retention_state"] = profile["retention_state"].astype("int8")
        profile["status_loss"] = profile["retention_state"].ne(0).astype("int8")
        if "retention_state_label" not in profile.columns:
            profile["retention_state_label"] = profile["retention_state"].map(
                state_labels
            )
    else:
        profile["retention_state"] = np.nan
        profile["retention_state_label"] = "검증값 없음"
        profile["status_loss"] = np.nan

    if "churn" in profile.columns:
        profile["churn"] = profile["churn"].astype("int8")
        profile["actual_result"] = np.where(
            profile["retention_state"].notna(),
            profile["retention_state_label"],
            np.where(profile["churn"].eq(1), "리뷰 활동 중단", "파워 지위 유지"),
        )
    else:
        profile["churn"] = np.nan
        profile["actual_result"] = "검증값 없음"

    if "selection_year" not in profile.columns:
        profile["selection_year"] = 2018
    if "comparison_year" not in profile.columns:
        profile["comparison_year"] = profile["selection_year"] - 1
    if "target_year" not in profile.columns:
        profile["target_year"] = profile["selection_year"] + 1
    if "sample_id" not in profile.columns:
        profile["sample_id"] = (
            profile["user_id"].astype(str)
            + "_"
            + profile["selection_year"].astype(str)
        )
    if "prior_activity_available" not in profile.columns:
        baseline = profile.get(
            "baseline_review_count",
            pd.Series(np.zeros(total), index=profile.index),
        )
        profile["prior_activity_available"] = baseline.gt(0).astype("int8")

    profile["model_version"] = model_version
    return enrich_profiles(profile)


def _derive_policy(profile: pd.DataFrame) -> pd.DataFrame:
    if profile.empty or not profile["retention_state"].notna().any():
        return pd.DataFrame()
    target = profile[profile["crm_target"].eq(1)]
    status_loss = profile["retention_state"].ne(0)
    selected_status_loss = target["retention_state"].ne(0)
    captured_status_loss = int(selected_status_loss.sum())
    total_status_loss = int(status_loss.sum())
    stopped_total = int(profile["retention_state"].eq(2).sum())
    weakened_total = int(profile["retention_state"].eq(1).sum())
    stopped_captured = int(target["retention_state"].eq(2).sum())
    weakened_captured = int(target["retention_state"].eq(1).sum())
    precision = captured_status_loss / len(target) if len(target) else 0
    base_rate = total_status_loss / len(profile) if len(profile) else 0
    return pd.DataFrame(
        [
            {
                "policy": "Unified Top 20% review queue",
                "target_rate": len(target) / len(profile),
                "target_users": len(target),
                "status_loss_captured": captured_status_loss,
                "status_loss_precision": precision,
                "status_loss_recall": (
                    captured_status_loss / total_status_loss
                    if total_status_loss
                    else 0
                ),
                "status_loss_lift": precision / base_rate if base_rate else np.nan,
                "stopped_captured": stopped_captured,
                "stopped_recall": (
                    stopped_captured / stopped_total if stopped_total else 0
                ),
                "weakened_captured": weakened_captured,
                "weakened_recall": (
                    weakened_captured / weakened_total if weakened_total else 0
                ),
            }
        ]
    )


def operational_profile_export(
    profiles: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    """Return a frontend-safe worklist without any post-outcome truth columns."""
    allowed = [
        *OPERATIONAL_ID_COLUMNS,
        *feature_columns,
        *OPERATIONAL_MODEL_COLUMNS,
    ]
    columns = [
        column
        for column in dict.fromkeys(allowed)
        if column in profiles.columns and column not in VALIDATION_ONLY_COLUMNS
    ]
    return profiles.loc[:, columns].copy()


def _load_optional(
    root: Path,
    key: str,
    warnings: list[str],
    sources: dict[str, str],
) -> pd.DataFrame | None:
    path = _first_path(root, OPTIONAL_FILE_CANDIDATES[key])
    if path is None:
        return None
    try:
        value = _read_table(str(path))
    except Exception as error:
        warnings.append(f"{path.name} 로드 실패: {error}")
        return None
    sources[key] = str(path)
    return value


def _load_v04_core(
    root: Path,
    sources: dict[str, str],
) -> dict[str, Any] | None:
    paths = {key: root / relative for key, relative in V04_CORE_FILES.items()}
    existing = {key: path.exists() for key, path in paths.items()}
    if not any(existing.values()):
        return None
    missing = [paths[key].name for key, exists in existing.items() if not exists]
    if missing:
        raise RuntimeError(
            "v04 핵심 산출물 묶음이 불완전합니다: " + ", ".join(missing)
        )

    values: dict[str, Any] = {}
    for key, path in paths.items():
        values[key] = (
            _read_json(str(path))
            if path.suffix.lower() == ".json"
            else _read_table(str(path))
        )
        sources[key] = str(path)

    metadata = values["model_metadata"]
    profiles = values["reviewer_profiles"]
    if metadata.get("version") != "v04":
        raise RuntimeError("v04 메타데이터의 version 값이 v04가 아닙니다.")
    if int(metadata.get("test_samples", -1)) != len(profiles):
        raise RuntimeError("v04 메타데이터와 프로필의 Test 표본 수가 다릅니다.")
    if not profiles["selection_year"].eq(metadata["test_selection_year"]).all():
        raise RuntimeError("v04 프로필 선정 연도가 메타데이터와 다릅니다.")
    if not profiles["target_year"].eq(metadata["test_target_year"]).all():
        raise RuntimeError("v04 프로필 타깃 연도가 메타데이터와 다릅니다.")

    validation = values["multiclass_validation"]
    final_rows = validation.loc[validation["record_type"].eq("final_test")]
    if len(final_rows) != 1:
        raise RuntimeError("v04 검증 결과의 final_test 행이 정확히 1개가 아닙니다.")
    final_row = final_rows.iloc[0]
    for metric in ["macro_f1", "macro_pr_auc", "macro_ovr_roc_auc"]:
        if not np.isclose(
            float(final_row[metric]),
            float(metadata["test_metrics"][metric]),
        ):
            raise RuntimeError(f"v04 검증 결과의 {metric}이 메타데이터와 다릅니다.")

    top_k = values["multiclass_top_k"]
    top20 = top_k.loc[
        top_k["split"].eq("final_test")
        & top_k["ranking"].eq("unified")
        & np.isclose(top_k["target_rate"], 0.20)
    ]
    if len(top20) != 1:
        raise RuntimeError("v04 Top-K 결과의 final_test 통합 상위 20% 행이 없습니다.")
    top20_row = top20.iloc[0]
    for metric, expected in metadata["top20_policy"].items():
        if metric in top20_row and not np.isclose(
            float(top20_row[metric]),
            float(expected),
        ):
            raise RuntimeError(f"v04 Top-K 결과의 {metric}이 메타데이터와 다릅니다.")

    confusion = values["multiclass_confusion"]
    final_confusion = confusion.loc[confusion["split"].eq("final_test")]
    if len(final_confusion) != 9 or int(final_confusion["users"].sum()) != len(
        profiles
    ):
        raise RuntimeError("v04 혼동행렬의 final_test 표본 수가 프로필과 다릅니다.")
    return values


def _load_v04_explainability(
    root: Path,
    metadata: dict[str, Any],
    warnings: list[str],
    sources: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = {
        key: root / relative
        for key, relative in V04_EXPLAINABILITY_FILES.items()
    }
    existing = {key: path.exists() for key, path in paths.items()}
    if not any(existing.values()):
        warnings.append(
            "v04 피처 중요도 묶음이 없어 신뢰 센터의 중요도 영역을 비활성화했습니다."
        )
        return pd.DataFrame(), pd.DataFrame()
    if not all(existing.values()):
        missing = [paths[key].name for key, exists in existing.items() if not exists]
        warnings.append(
            "v04 피처 중요도 묶음이 불완전해 표시하지 않습니다: "
            + ", ".join(missing)
        )
        return pd.DataFrame(), pd.DataFrame()

    feature = _read_table(str(paths["feature_importance"]))
    group = _read_table(str(paths["group_importance"]))
    expected_features = set(metadata.get("feature_columns", []))
    baseline_pr_auc = float(metadata["test_metrics"]["macro_pr_auc"])

    valid = (
        len(feature) == int(metadata.get("feature_count", -1))
        and set(feature["feature"]) == expected_features
        and int(group["feature_count"].sum()) == int(metadata["feature_count"])
        and feature["model_version"].eq("v04").all()
        and group["model_version"].eq("v04").all()
        and feature["split"].eq("final_test").all()
        and group["split"].eq("final_test").all()
        and feature["method"].eq("single_feature_permutation").all()
        and group["method"].eq("joint_group_permutation").all()
        and feature["repeats"].eq(20).all()
        and group["repeats"].eq(20).all()
        and np.allclose(feature["baseline_pr_auc"], baseline_pr_auc)
        and np.allclose(group["baseline_pr_auc"], baseline_pr_auc)
        and np.isfinite(
            feature[["importance_mean", "importance_std"]].to_numpy()
        ).all()
        and np.isfinite(
            group[["importance_mean", "importance_std"]].to_numpy()
        ).all()
    )
    if not valid:
        warnings.append(
            "v04 피처 중요도 계약이 메타데이터와 달라 표시하지 않습니다."
        )
        return pd.DataFrame(), pd.DataFrame()

    sources["feature_importance"] = str(paths["feature_importance"])
    sources["group_importance"] = str(paths["group_importance"])
    return feature, group


def _load_v03_comparison(
    root: Path,
    warnings: list[str],
    sources: dict[str, str],
) -> dict[str, pd.DataFrame]:
    empty = {
        key: pd.DataFrame()
        for key in V03_COMPARISON_FILES
    }
    paths = {
        key: root / relative
        for key, relative in V03_COMPARISON_FILES.items()
    }
    existing = {key: path.exists() for key, path in paths.items()}
    if not any(existing.values()):
        return empty
    if not all(existing.values()):
        missing = [paths[key].name for key, exists in existing.items() if not exists]
        warnings.append(
            "v03 비교 산출물 묶음이 불완전해 표시하지 않습니다: "
            + ", ".join(missing)
        )
        return empty

    try:
        values = {
            key: _read_table(str(path))
            for key, path in paths.items()
        }
        validation = values["multiclass_validation_v03"]
        final_rows = validation.loc[validation["record_type"].eq("final_test")]
        if len(final_rows) != 1:
            raise ValueError("검증 결과의 final_test 행이 정확히 1개가 아닙니다.")
        final_row = final_rows.iloc[0]
        test_samples = int(final_row["validation_samples"])
        baseline_pr_auc = float(final_row["macro_pr_auc"])

        top_k = values["multiclass_top_k_v03"]
        top20 = top_k.loc[
            top_k["split"].eq("final_test")
            & top_k["ranking"].eq("unified")
            & np.isclose(top_k["target_rate"], 0.20)
        ]
        if len(top20) != 1:
            raise ValueError("Top-K 결과의 final_test 통합 상위 20% 행이 없습니다.")

        confusion = values["multiclass_confusion_v03"]
        final_confusion = confusion.loc[confusion["split"].eq("final_test")]
        if "decision_policy" in final_confusion.columns:
            final_confusion = final_confusion.loc[
                final_confusion["decision_policy"].eq("threshold")
            ]
        if len(final_confusion) != 9 or int(final_confusion["users"].sum()) != test_samples:
            raise ValueError("혼동행렬의 final_test 표본 수가 검증 결과와 다릅니다.")

        feature = values["feature_importance_v03"]
        group = values["group_importance_v03"]
        if (
            len(feature) != 43
            or int(group["feature_count"].sum()) != 43
            or not np.allclose(group["baseline_pr_auc"], baseline_pr_auc)
        ):
            raise ValueError("피처 중요도 계약이 v03 검증 결과와 다릅니다.")
    except Exception as error:
        warnings.append(f"v03 비교 산출물 계약 오류로 표시하지 않습니다: {error}")
        return empty

    for key, path in paths.items():
        sources[key] = str(path)
    return values


@st.cache_resource(show_spinner=False)
def load_app_data() -> AppData:
    root = find_project_root()
    paths = project_paths(root)
    warnings: list[str] = []
    sources: dict[str, str] = {}

    try:
        core = _load_v04_core(root, sources)
    except Exception as error:
        raise RuntimeError(f"v04 데이터 묶음을 불러올 수 없습니다: {error}") from error

    if core is None:
        demo = build_demo_data()
        demo_profiles = _normalize_profiles(
            demo.reviewer_profiles,
            model_version="v04",
        )
        warnings.append(
            "프로젝트 v04 핵심 산출물을 찾지 못해 익명 합성 데모 데이터를 "
            "사용하고 있습니다."
        )
        return AppData(
            paths=paths,
            data_mode="demo",
            model_version="v04",
            comparison_year=2017,
            selection_year=2018,
            target_year=2019,
            reviewer_profiles=demo_profiles,
            primary_policy=_derive_policy(demo_profiles),
            feature_importance=demo.feature_importance,
            group_importance=demo.group_importance,
            model_metadata=demo.model_metadata,
            multiclass_validation=demo.multiclass_validation,
            multiclass_top_k=demo.multiclass_top_k,
            multiclass_confusion=demo.multiclass_confusion,
            warnings=warnings,
            sources={"reviewer_profiles": "built-in v04 demo"},
        )

    metadata = core["model_metadata"]
    profiles = _normalize_profiles(
        core["reviewer_profiles"],
        model_version=str(metadata["version"]),
    )
    feature_importance, group_importance = _load_v04_explainability(
        root,
        metadata,
        warnings,
        sources,
    )
    v03_comparison = _load_v03_comparison(root, warnings, sources)

    optional: dict[str, pd.DataFrame | None] = {}
    for key in OPTIONAL_FILE_CANDIDATES:
        optional[key] = _load_optional(root, key, warnings, sources)

    comparison_year = int(profiles["comparison_year"].iloc[0])
    selection_year = int(metadata["test_selection_year"])
    target_year = int(metadata["test_target_year"])
    retention_distribution = (
        profiles.groupby(["selection_year", "target_year", "retention_state"])
        .size()
        .rename("users")
        .reset_index()
    )

    return AppData(
        paths=paths,
        data_mode="project",
        model_version=str(metadata["version"]),
        comparison_year=comparison_year,
        selection_year=selection_year,
        target_year=target_year,
        reviewer_profiles=profiles,
        top_k=optional["top_k"] if optional["top_k"] is not None else pd.DataFrame(),
        primary_policy=_derive_policy(profiles),
        validation_test=(
            optional["validation_test"]
            if optional["validation_test"] is not None
            else pd.DataFrame()
        ),
        feature_importance=feature_importance,
        group_importance=group_importance,
        multiclass_validation_v03=v03_comparison["multiclass_validation_v03"],
        multiclass_top_k_v03=v03_comparison["multiclass_top_k_v03"],
        multiclass_confusion_v03=v03_comparison["multiclass_confusion_v03"],
        feature_importance_v03=v03_comparison["feature_importance_v03"],
        group_importance_v03=v03_comparison["group_importance_v03"],
        feature_importance_v02=(
            optional["feature_importance_v02"]
            if optional["feature_importance_v02"] is not None
            else pd.DataFrame()
        ),
        group_importance_v02=(
            optional["group_importance_v02"]
            if optional["group_importance_v02"] is not None
            else pd.DataFrame()
        ),
        feature_sets=(
            optional["feature_sets"]
            if optional["feature_sets"] is not None
            else pd.DataFrame()
        ),
        reviewer_monthly_activity=(
            optional["reviewer_monthly_activity"]
            if optional["reviewer_monthly_activity"] is not None
            else pd.DataFrame()
        ),
        regional_risk=(
            optional["regional_risk"]
            if optional["regional_risk"] is not None
            else pd.DataFrame()
        ),
        model_metadata=metadata,
        retention_distribution=retention_distribution,
        multiclass_validation=core["multiclass_validation"],
        multiclass_top_k=core["multiclass_top_k"],
        multiclass_confusion=core["multiclass_confusion"],
        warnings=warnings,
        sources=sources,
    )
