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
    risk_tiers: pd.DataFrame = field(default_factory=pd.DataFrame)
    top_k: pd.DataFrame = field(default_factory=pd.DataFrame)
    primary_policy: pd.DataFrame = field(default_factory=pd.DataFrame)
    validation_test: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_importance: pd.DataFrame = field(default_factory=pd.DataFrame)
    group_importance: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_sets: pd.DataFrame = field(default_factory=pd.DataFrame)
    split_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    reviewer_monthly_activity: pd.DataFrame = field(default_factory=pd.DataFrame)
    regional_risk: pd.DataFrame = field(default_factory=pd.DataFrame)
    model_metadata: dict[str, Any] = field(default_factory=dict)
    risk_policy: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)


FILE_CANDIDATES = {
    "reviewer_profiles": [
        "data/processed/predictions/final_reviewer_risk_profiles_v02.parquet",
        "data/processed/final_reviewer_risk_profiles_v02.parquet",
    ],
    "risk_tiers": [
        "reports/tables/final_risk_tier_summary_v02.csv",
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
        "reports/tables/final_feature_importance_v02.csv",
    ],
    "group_importance": [
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
        "models/final_core_hgb_metadata_v02.json",
        "models/metadata/final_core_hgb_metadata_v02.json",
    ],
    "risk_policy": [
        "data/processed/predictions/risk_policy_v02.json",
        "configs/risk_policy_v02.json",
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
        "Top 20% 관리 대상",
        "일반 모니터링",
    )

    if "churn" in profile.columns:
        profile["churn"] = profile["churn"].fillna(0).astype("int8")
        profile["actual_result"] = np.where(profile["churn"].eq(1), "이탈", "유지")
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


def _derive_risk_tiers(profile: pd.DataFrame) -> pd.DataFrame:
    total = len(profile)
    total_churn = float(profile["churn"].sum()) if profile["churn"].notna().any() else 0
    overall_rate = total_churn / total if total else 0
    rows: list[dict[str, Any]] = []
    for tier in ["긴급 관리", "집중 관리", "관찰 대상", "일반"]:
        subset = profile[profile["risk_tier"].eq(tier)]
        if subset.empty:
            continue
        churn_users = (
            int(subset["churn"].sum()) if subset["churn"].notna().any() else 0
        )
        observed = churn_users / len(subset) if len(subset) else 0
        rows.append(
            {
                "risk_tier": tier,
                "users": len(subset),
                "churn_users": churn_users,
                "observed_churn_rate": observed,
                "mean_risk_score": subset["risk_score"].mean(),
                "minimum_risk_score": subset["risk_score"].min(),
                "maximum_risk_score": subset["risk_score"].max(),
                "user_rate": len(subset) / total,
                "captured_churn_rate": (
                    churn_users / total_churn if total_churn else np.nan
                ),
                "lift": observed / overall_rate if overall_rate else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _derive_policy(profile: pd.DataFrame) -> pd.DataFrame:
    if profile.empty or not profile["churn"].notna().any():
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
        warnings.append(
            "프로젝트 위험 프로필 파일을 찾지 못해 검증 결과와 동일한 "
            "내장 데모 데이터를 사용하고 있습니다."
        )
        return AppData(
            paths=paths,
            data_mode="demo",
            reviewer_profiles=enrich_profiles(demo.reviewer_profiles),
            risk_tiers=demo.risk_tiers,
            top_k=demo.top_k,
            primary_policy=demo.primary_policy,
            validation_test=demo.validation_test,
            feature_importance=demo.feature_importance,
            group_importance=demo.group_importance,
            feature_sets=demo.feature_sets,
            split_summary=demo.split_summary,
            model_metadata=demo.model_metadata,
            risk_policy=demo.risk_policy,
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
        "risk_tiers",
        "top_k",
        "primary_policy",
        "validation_test",
        "feature_importance",
        "group_importance",
        "feature_sets",
        "split_summary",
        "reviewer_monthly_activity",
        "regional_risk",
        "model_metadata",
        "risk_policy",
    ]:
        values[key] = _load_optional(root, key, warnings, sources)

    if values["risk_tiers"] is None:
        values["risk_tiers"] = _derive_risk_tiers(profiles)
        warnings.append("위험 등급 요약은 리뷰어 프로필에서 재계산했습니다.")
    if values["primary_policy"] is None:
        values["primary_policy"] = _derive_policy(profiles)
        warnings.append("Top 20% 정책 성과는 리뷰어 프로필에서 재계산했습니다.")
    if values["top_k"] is None:
        values["top_k"] = _derive_top_k(profiles)
        warnings.append("Top-K 성과는 리뷰어 프로필에서 재계산했습니다.")

    loaded_core = sum(
        key in sources
        for key in [
            "risk_tiers",
            "top_k",
            "primary_policy",
            "validation_test",
            "feature_importance",
            "group_importance",
            "feature_sets",
            "split_summary",
        ]
    )
    data_mode = "project" if loaded_core >= 6 else "hybrid"

    return AppData(
        paths=paths,
        data_mode=data_mode,
        reviewer_profiles=profiles,
        risk_tiers=values["risk_tiers"],
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
        warnings=warnings,
        sources=sources,
    )

