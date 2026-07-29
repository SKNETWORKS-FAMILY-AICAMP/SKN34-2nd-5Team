"""리뷰어 프로필 정규화. Streamlit·DB·파일 I/O에 의존하지 않는다.

archive/app_streamlit_v04/core/data.py의 `_numeric`/`_normalize_profiles`
원본이었으며, 그 파일은 이제 이 모듈을 import해서 쓴다(내부 사용 + 기존
`from core.data import _normalize_profiles` 경로 재노출).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from shared.retention.insights import enrich_profiles


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
