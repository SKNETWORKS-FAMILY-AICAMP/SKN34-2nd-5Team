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
    reviewer_profiles: pd.DataFrame = field(default_factory=pd.DataFrame)
    top_k: pd.DataFrame = field(default_factory=pd.DataFrame)
    primary_policy: pd.DataFrame = field(default_factory=pd.DataFrame)
    validation_test: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_importance: pd.DataFrame = field(default_factory=pd.DataFrame)
    group_importance: pd.DataFrame = field(default_factory=pd.DataFrame)
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


FILE_CANDIDATES = {
    "reviewer_profiles": [
        "data/processed/predictions/final_test_retention_profiles_v03.parquet",
        "data/processed/predictions/final_reviewer_risk_profiles_v02.parquet",
        "data/processed/final_reviewer_risk_profiles_v02.parquet",
    ],
    "top_k": [
        "reports/tables/final_test_top_k_performance_v02.csv",
    ],
    "primary_policy": [
        "reports/tables/final_test_primary_policy_v02.csv",
    ],
    "validation_test": [
        "reports/tables/validation_test_comparison_v02.csv",
        "reports/tables/final_validation_test_comparison_v02.csv",
    ],
    "feature_importance": [
        "reports/tables/final_feature_importance_v03.csv",
        "reports/tables/final_feature_importance_v02.csv",
    ],
    "group_importance": [
        "reports/tables/final_feature_group_importance_v03.csv",
        "reports/tables/final_feature_group_importance_v02.csv",
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
    "split_summary": [
        "reports/tables/rolling_temporal_split_summary_v02.csv",
    ],
    "reviewer_monthly_activity": [
        "data/processed/predictions/reviewer_monthly_activity_v01.parquet",
        "data/processed/reviewer_monthly_activity_v01.parquet",
    ],
    "regional_risk": [
        "reports/tables/regional_risk_summary_v01.csv",
        "data/processed/regional_risk_summary_v01.parquet",
    ],
    "model_metadata": [
        "models/final_core_logistic_multiclass_metadata_v03.json",
        "models/final_core_hgb_metadata_v02.json",
        "models/metadata/final_core_hgb_metadata_v02.json",
    ],
    "risk_policy": [
        "data/processed/predictions/risk_policy_v02.json",
        "configs/risk_policy_v02.json",
    ],
    "retention_distribution": [
        "reports/tables/retention_state_distribution_v03.csv",
    ],
    "multiclass_validation": [
        "reports/tables/multiclass_validation_results_v03.csv",
    ],
    "multiclass_top_k": [
        "reports/tables/multiclass_top_k_performance_v03.csv",
    ],
    "multiclass_confusion": [
        "reports/tables/multiclass_confusion_matrix_v03.csv",
    ],
}


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

    unique_candidates = list(dict.fromkeys(candidates))
    profile_relative = FILE_CANDIDATES["reviewer_profiles"][0]
    for candidate in unique_candidates:
        if (candidate / profile_relative).exists():
            return candidate
    for candidate in unique_candidates:
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


def _normalize_profiles(frame: pd.DataFrame) -> pd.DataFrame:
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
            "selection_year",
            "target_year",
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
        profile["retention_state"] = (
            profile["retention_state"].fillna(0).astype("int8")
        )
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
        profile["churn"] = profile["churn"].fillna(0).astype("int8")
        profile["actual_result"] = np.where(
            profile["retention_state"].notna(),
            profile["retention_state_label"],
            np.where(profile["churn"].eq(1), "리뷰 활동 중단", "파워 지위 유지"),
        )
    else:
        profile["churn"] = np.nan
        profile["actual_result"] = "검증값 없음"

    if "sample_id" not in profile.columns:
        selection = (
            profile["selection_year"].fillna("NA").astype(str)
            if "selection_year" in profile.columns
            else pd.Series(["NA"] * total)
        )
        profile["sample_id"] = selection + "_" + profile["user_id"].astype(str)
    if "selection_year" not in profile.columns:
        profile["selection_year"] = 2017
    if "target_year" not in profile.columns:
        profile["target_year"] = 2019

    return enrich_profiles(profile)


def _derive_policy(profile: pd.DataFrame) -> pd.DataFrame:
    if profile.empty:
        return pd.DataFrame()
    if "retention_state" in profile and profile["retention_state"].notna().any():
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
    if not profile["churn"].notna().any():
        return pd.DataFrame()
    target = profile[profile["crm_target"].eq(1)]
    non_target = profile[profile["crm_target"].eq(0)]
    tp = int(target["churn"].sum())
    fp = int(len(target) - tp)
    fn = int(non_target["churn"].sum())
    tn = int(len(non_target) - fn)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    base_rate = float(profile["churn"].mean())
    return pd.DataFrame(
        [
            {
                "policy": "Top 20% CRM targeting",
                "target_rate": len(target) / len(profile),
                "target_users": len(target),
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "true_negative": tn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "lift": precision / base_rate if base_rate else np.nan,
            }
        ]
    )


def _derive_top_k(profile: pd.DataFrame) -> pd.DataFrame:
    if profile.empty or not profile["churn"].notna().any():
        return pd.DataFrame()
    ordered = profile.sort_values("risk_score", ascending=False).reset_index(drop=True)
    total_churn = int(ordered["churn"].sum())
    base_rate = float(ordered["churn"].mean())
    rows = []
    for rate in [5, 10, 15, 20, 25, 30, 35, 40]:
        count = int(np.ceil(len(ordered) * rate / 100))
        subset = ordered.head(count)
        captured = int(subset["churn"].sum())
        precision = captured / count if count else 0
        recall = captured / total_churn if total_churn else 0
        rows.append(
            {
                "target_rate_pct": float(rate),
                "target_users": count,
                "captured_churn_users": captured,
                "precision_at_k": precision,
                "recall_at_k": recall,
                "lift_at_k": precision / base_rate if base_rate else np.nan,
                "minimum_risk_score": subset["risk_score"].min(),
            }
        )
    return pd.DataFrame(rows)


def _load_optional(
    root: Path,
    key: str,
    warnings: list[str],
    sources: dict[str, str],
) -> pd.DataFrame | dict[str, Any] | None:
    path = _first_path(root, FILE_CANDIDATES[key])
    if path is None:
        return None
    try:
        value = _read_json(str(path)) if path.suffix == ".json" else _read_table(str(path))
    except Exception as error:
        warnings.append(f"{path.name} 로드 실패: {error}")
        return None
    sources[key] = str(path)
    return value


@st.cache_resource(show_spinner=False)
def load_app_data() -> AppData:
    root = find_project_root()
    paths = project_paths(root)
    warnings: list[str] = []
    sources: dict[str, str] = {}

    profile_path = _first_path(root, FILE_CANDIDATES["reviewer_profiles"])
    if profile_path is None:
        demo = build_demo_data()
        demo_profiles = _normalize_profiles(demo.reviewer_profiles)
        warnings.append(
            "프로젝트 v03 리뷰어 프로필 파일을 찾지 못해 집계 결과와 동일한 "
            "익명 합성 데모 데이터를 사용하고 있습니다."
        )
        return AppData(
            paths=paths,
            data_mode="demo",
            reviewer_profiles=demo_profiles,
            top_k=demo.top_k,
            primary_policy=_derive_policy(demo_profiles),
            validation_test=demo.validation_test,
            feature_importance=demo.feature_importance,
            group_importance=demo.group_importance,
            feature_sets=demo.feature_sets,
            split_summary=demo.split_summary,
            model_metadata=demo.model_metadata,
            risk_policy=demo.risk_policy,
            retention_distribution=demo.retention_distribution,
            multiclass_validation=demo.multiclass_validation,
            multiclass_top_k=demo.multiclass_top_k,
            multiclass_confusion=demo.multiclass_confusion,
            warnings=warnings,
            sources={"reviewer_profiles": "built-in demo"},
        )

    try:
        profiles = _normalize_profiles(_read_table(str(profile_path)))
    except Exception as error:
        raise RuntimeError(f"리뷰어 위험 프로필을 불러올 수 없습니다: {error}") from error
    sources["reviewer_profiles"] = str(profile_path)

    values: dict[str, Any] = {}
    for key in [
        "top_k",
        "primary_policy",
        "validation_test",
        "feature_importance",
        "group_importance",
        "feature_importance_v02",
        "group_importance_v02",
        "feature_sets",
        "split_summary",
        "reviewer_monthly_activity",
        "regional_risk",
        "model_metadata",
        "risk_policy",
        "retention_distribution",
        "multiclass_validation",
        "multiclass_top_k",
        "multiclass_confusion",
    ]:
        values[key] = _load_optional(root, key, warnings, sources)

    is_v03 = "priority_score" in profiles.columns
    if is_v03 or values["primary_policy"] is None:
        values["primary_policy"] = _derive_policy(profiles)
        if not is_v03:
            warnings.append("Top 20% 정책 성과는 리뷰어 프로필에서 재계산했습니다.")
    if values["top_k"] is None:
        values["top_k"] = _derive_top_k(profiles)
        warnings.append("Top-K 성과는 리뷰어 프로필에서 재계산했습니다.")

    loaded_core = sum(
        key in sources
        for key in [
            "reviewer_profiles",
            "retention_distribution",
            "multiclass_validation",
            "multiclass_top_k",
            "multiclass_confusion",
            "model_metadata",
        ]
    )
    data_mode = "project" if loaded_core >= 5 else "hybrid"

    return AppData(
        paths=paths,
        data_mode=data_mode,
        reviewer_profiles=profiles,
        top_k=values["top_k"],
        primary_policy=values["primary_policy"],
        validation_test=values["validation_test"]
        if values["validation_test"] is not None
        else pd.DataFrame(),
        feature_importance=values["feature_importance"]
        if values["feature_importance"] is not None
        else pd.DataFrame(),
        group_importance=values["group_importance"]
        if values["group_importance"] is not None
        else pd.DataFrame(),
        feature_importance_v02=values["feature_importance_v02"]
        if values["feature_importance_v02"] is not None
        else pd.DataFrame(),
        group_importance_v02=values["group_importance_v02"]
        if values["group_importance_v02"] is not None
        else pd.DataFrame(),
        feature_sets=values["feature_sets"]
        if values["feature_sets"] is not None
        else pd.DataFrame(),
        split_summary=values["split_summary"]
        if values["split_summary"] is not None
        else pd.DataFrame(),
        reviewer_monthly_activity=values["reviewer_monthly_activity"]
        if values["reviewer_monthly_activity"] is not None
        else pd.DataFrame(),
        regional_risk=values["regional_risk"]
        if values["regional_risk"] is not None
        else pd.DataFrame(),
        model_metadata=values["model_metadata"]
        if isinstance(values["model_metadata"], dict)
        else {},
        risk_policy=values["risk_policy"]
        if isinstance(values["risk_policy"], dict)
        else {},
        retention_distribution=values["retention_distribution"]
        if values["retention_distribution"] is not None
        else pd.DataFrame(),
        multiclass_validation=values["multiclass_validation"]
        if values["multiclass_validation"] is not None
        else pd.DataFrame(),
        multiclass_top_k=values["multiclass_top_k"]
        if values["multiclass_top_k"] is not None
        else pd.DataFrame(),
        multiclass_confusion=values["multiclass_confusion"]
        if values["multiclass_confusion"] is not None
        else pd.DataFrame(),
        warnings=warnings,
        sources=sources,
    )
