from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


TIER_SPECS = [
    ("긴급 관리", 208, 112, 0.8465, 0.7790),
    ("집중 관리", 624, 234, 0.7786, 0.6579),
    ("관찰 대상", 831, 185, 0.6574, 0.4110),
    ("일반", 2_494, 139, 0.4109, 0.0232),
]


@dataclass
class DemoData:
    reviewer_profiles: pd.DataFrame
    risk_tiers: pd.DataFrame
    top_k: pd.DataFrame
    primary_policy: pd.DataFrame
    validation_test: pd.DataFrame
    feature_importance: pd.DataFrame
    group_importance: pd.DataFrame
    feature_sets: pd.DataFrame
    split_summary: pd.DataFrame
    model_metadata: dict[str, Any]
    risk_policy: dict[str, Any]


def _banded_churn(total: int) -> np.ndarray:
    """Reproduce the validated Test Top-K counts without exposing real user IDs."""
    band_sizes = [208, 208, 208, 208, 208, 208, 207, 208, 2_494]
    band_churn = [112, 90, 79, 65, 51, 51, 42, 41, 139]
    rng = np.random.default_rng(34)
    labels: list[np.ndarray] = []
    for size, positives in zip(band_sizes, band_churn):
        band = np.zeros(size, dtype="int8")
        chosen = rng.choice(size, size=positives, replace=False)
        band[chosen] = 1
        labels.append(band)
    result = np.concatenate(labels)
    assert len(result) == total
    assert int(result.sum()) == 670
    return result


def _profile_frame() -> pd.DataFrame:
    total = sum(spec[1] for spec in TIER_SPECS)
    rng = np.random.default_rng(3405)

    tiers: list[str] = []
    scores: list[float] = []
    for tier, users, _, maximum, minimum in TIER_SPECS:
        tiers.extend([tier] * users)
        scores.extend(np.linspace(maximum, minimum, users).tolist())

    frame = pd.DataFrame(
        {
            "risk_rank": np.arange(1, total + 1),
            "risk_tier": tiers,
            "risk_score": scores,
            "churn": _banded_churn(total),
        }
    )
    frame["sample_id"] = frame["risk_rank"].map(lambda value: f"2017_demo_{value:05d}")
    frame["user_id"] = frame["risk_rank"].map(lambda value: f"demo_reviewer_{value:05d}")
    frame["selection_year"] = 2017
    frame["target_year"] = 2019
    frame["risk_top_percent"] = frame["risk_rank"] / total * 100
    frame["risk_percentile"] = 100 - (frame["risk_rank"] - 1) / total * 100
    frame["crm_target"] = (frame["risk_rank"] <= 832).astype("int8")
    frame["crm_target_label"] = np.where(
        frame["crm_target"].eq(1),
        "Top 20% 관리 대상",
        "일반 모니터링",
    )
    frame["actual_result"] = np.where(frame["churn"].eq(1), "이탈", "유지")

    normalized_risk = (frame["risk_score"] - frame["risk_score"].min()) / (
        frame["risk_score"].max() - frame["risk_score"].min()
    )
    churn_boost = frame["churn"].astype(float)

    baseline_reviews = np.maximum(
        10,
        np.rint(rng.gamma(3.0, 5.1, total) + 9 + 4 * (1 - normalized_risk)),
    ).astype(int)
    decline = np.clip(
        0.08 + 0.56 * normalized_risk + 0.09 * churn_boost + rng.normal(0, 0.14, total),
        -0.35,
        0.94,
    )
    recent_reviews = np.maximum(
        1,
        np.rint(baseline_reviews * (1 - decline)),
    ).astype(int)
    actual_decline = 1 - recent_reviews / baseline_reviews

    baseline_months = np.clip(
        np.rint(8.2 - 2.3 * normalized_risk + rng.normal(0, 1.4, total)),
        3,
        12,
    ).astype(int)
    month_decline = np.clip(
        0.02 + 0.43 * normalized_risk + 0.07 * churn_boost + rng.normal(0, 0.12, total),
        -0.25,
        0.85,
    )
    recent_months = np.maximum(
        1,
        np.rint(baseline_months * (1 - month_decline)),
    ).astype(int)

    baseline_businesses = np.maximum(
        8,
        baseline_reviews - rng.binomial(np.minimum(baseline_reviews, 5), 0.18),
    )
    recent_businesses = np.maximum(
        1,
        recent_reviews - rng.binomial(np.minimum(recent_reviews, 4), 0.13),
    )
    business_decline = 1 - recent_businesses / baseline_businesses

    baseline_recency = np.clip(
        rng.gamma(2.2, 14.0, total) + 5,
        1,
        170,
    )
    recency_increase = np.clip(
        -4 + 48 * normalized_risk + 11 * churn_boost + rng.normal(0, 17, total),
        -55,
        170,
    )
    recent_recency = np.maximum(0, baseline_recency + recency_increase)

    baseline_interval = np.clip(
        rng.normal(15.6, 5.7, total),
        2,
        55,
    )
    interval_increase = np.clip(
        -1 + 29 * normalized_risk + 7 * churn_boost + rng.normal(0, 11, total),
        -30,
        130,
    )
    recent_interval = np.maximum(1, baseline_interval + interval_increase)

    frame["baseline_review_count"] = baseline_reviews
    frame["recent_review_count"] = recent_reviews
    frame["review_count_decline_rate"] = actual_decline
    frame["baseline_active_months"] = baseline_months
    frame["recent_active_months"] = recent_months
    frame["active_month_decline_rate"] = 1 - recent_months / baseline_months
    frame["baseline_unique_business_count"] = baseline_businesses
    frame["recent_unique_business_count"] = recent_businesses
    frame["unique_business_decline_rate"] = business_decline
    frame["baseline_recency_days"] = baseline_recency
    frame["recent_recency_days"] = recent_recency
    frame["recency_increase_days"] = recent_recency - baseline_recency
    frame["baseline_mean_interval_days"] = baseline_interval
    frame["recent_mean_interval_days"] = recent_interval
    frame["mean_interval_increase_days"] = recent_interval - baseline_interval

    return frame


def _risk_tier_summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "risk_tier": [spec[0] for spec in TIER_SPECS],
            "users": [spec[1] for spec in TIER_SPECS],
            "churn_users": [spec[2] for spec in TIER_SPECS],
            "observed_churn_rate": [0.5385, 0.3750, 0.2226, 0.0557],
            "mean_risk_score": [0.8047, 0.7215, 0.5418, 0.1703],
            "minimum_risk_score": [0.7790, 0.6579, 0.4110, 0.0232],
            "maximum_risk_score": [0.8465, 0.7786, 0.6574, 0.4109],
            "user_rate": [0.0500, 0.1501, 0.1999, 0.6000],
            "captured_churn_rate": [0.1672, 0.3493, 0.2761, 0.2075],
            "lift": [3.3409, 2.3267, 1.3813, 0.3458],
        }
    )


def _top_k() -> pd.DataFrame:
    target_rate = [5, 10, 15, 20, 25, 30, 35, 40]
    target_users = [208, 416, 624, 832, 1_040, 1_248, 1_455, 1_663]
    captured = [112, 202, 281, 346, 397, 448, 490, 531]
    precision = [0.5385, 0.4856, 0.4503, 0.4159, 0.3817, 0.3590, 0.3368, 0.3193]
    recall = [0.1672, 0.3015, 0.4194, 0.5164, 0.5925, 0.6687, 0.7313, 0.7925]
    lift = [3.34, 3.01, 2.79, 2.58, 2.37, 2.23, 2.09, 1.98]
    minimum_score = [0.7790, 0.7409, 0.7024, 0.6579, 0.6040, 0.5511, 0.4782, 0.4110]
    return pd.DataFrame(
        {
            "target_rate_pct": target_rate,
            "target_users": target_users,
            "captured_churn_users": captured,
            "precision_at_k": precision,
            "recall_at_k": recall,
            "lift_at_k": lift,
            "minimum_risk_score": minimum_score,
        }
    )


def _feature_importance() -> pd.DataFrame:
    rows = [
        ("activity", "recent_active_months", 0.10151, 0.01333, 45.01969),
        ("interval", "recent_recency_days", 0.07113, 0.00498, 31.54586),
        ("activity", "recent_review_count", 0.01355, 0.00507, 6.00738),
        ("interval", "baseline_recency_days", 0.01010, 0.00296, 4.47940),
        ("interval", "baseline_median_interval_days", 0.00372, 0.00237, 1.64955),
        ("activity", "baseline_active_months", 0.00335, 0.00144, 1.48374),
        ("business", "baseline_new_business_rate", 0.00299, 0.00155, 1.32704),
        ("interval", "recent_mean_interval_days", 0.00275, 0.00127, 1.21809),
        ("interval", "recency_increase_days", 0.00231, 0.00161, 1.02338),
        ("interval", "recent_max_interval_days", 0.00222, 0.00270, 0.98665),
        ("activity", "review_count_ratio", 0.00219, 0.00218, 0.97086),
        ("interval", "baseline_mean_interval_days", 0.00201, 0.00096, 0.89026),
        ("business", "recent_new_business_rate", 0.00157, 0.00098, 0.69805),
        ("interval", "recent_median_interval_days", 0.00140, 0.00123, 0.62059),
        ("activity", "baseline_reviews_per_active_month", 0.00133, 0.00428, 0.59100),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "feature_group",
            "feature",
            "importance_mean",
            "importance_std",
            "importance_share_pct",
        ],
    )
    frame.insert(0, "rank", np.arange(1, len(frame) + 1))
    return frame


def build_demo_data() -> DemoData:
    profiles = _profile_frame()
    risk_tiers = _risk_tier_summary()
    top_k = _top_k()
    policy = pd.DataFrame(
        [
            {
                "policy": "Top 20% CRM targeting",
                "target_rate": 0.20,
                "target_users": 832,
                "true_positive": 346,
                "false_positive": 486,
                "false_negative": 324,
                "true_negative": 3_001,
                "precision": 0.4159,
                "recall": 0.5164,
                "f1": 0.4607,
                "lift": 2.5802,
            }
        ]
    )
    validation_test = pd.DataFrame(
        [
            {
                "dataset": "Validation",
                "selection_year": 2016,
                "target_year": 2018,
                "precision": 0.3107,
                "recall": 0.7476,
                "f1": 0.4390,
                "roc_auc": 0.8146,
                "pr_auc": 0.4032,
            },
            {
                "dataset": "Test",
                "selection_year": 2017,
                "target_year": 2019,
                "precision": 0.3436,
                "recall": 0.7134,
                "f1": 0.4639,
                "roc_auc": 0.8125,
                "pr_auc": 0.4264,
            },
        ]
    )
    group_importance = pd.DataFrame(
        {
            "feature_group": ["activity", "interval", "business"],
            "feature_count": [15, 13, 15],
            "importance_mean": [0.13656, 0.11170, 0.00600],
            "importance_std": [0.01304, 0.00530, 0.00389],
            "baseline_pr_auc": [0.42641, 0.42641, 0.42641],
            "rank": [1, 2, 3],
        }
    )
    feature_sets = pd.DataFrame(
        [
            ("01_core", 43, 0.3107, 0.7476, 0.4390, 0.8146, 0.4032),
            ("02_core+category", 57, 0.3192, 0.7723, 0.4517, 0.8146, 0.3854),
            ("03_core+spatial", 55, 0.3167, 0.7362, 0.4429, 0.8152, 0.3986),
            ("04_core+rating", 55, 0.3080, 0.7533, 0.4372, 0.8106, 0.3970),
            ("05_core+category+spatial", 69, 0.3186, 0.7647, 0.4498, 0.8177, 0.3991),
            ("06_all", 81, 0.3173, 0.7514, 0.4462, 0.8156, 0.3991),
        ],
        columns=[
            "feature_set",
            "feature_count",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "pr_auc",
        ],
    )
    feature_sets["model"] = "HistGradientBoosting"
    split_summary = pd.DataFrame(
        [
            ("train", 13_720, 8_483, 2009, 2015, 2_189, 15.95),
            ("validation", 3_724, 3_724, 2016, 2016, 527, 14.15),
            ("test", 4_157, 4_157, 2017, 2017, 670, 16.12),
        ],
        columns=[
            "split",
            "samples",
            "unique_users",
            "minimum_selection_year",
            "maximum_selection_year",
            "churn_samples",
            "churn_rate_pct",
        ],
    )
    metadata = {
        "model_type": "HistGradientBoostingClassifier",
        "feature_set": "activity + interval + business",
        "feature_count": 43,
        "train_selection_years": "2009~2015",
        "validation_selection_year": 2016,
        "test_selection_year": 2017,
        "test_target_year": 2019,
        "primary_target_policy": "Top 20%",
        "risk_score_warning": (
            "class_weight가 적용된 확률 보정 전 점수이므로 "
            "위험 순위와 등급으로 해석합니다."
        ),
    }
    policy_json = {
        "version": "v02",
        "primary_policy": "top_20_percent",
        "tiers": {
            "critical": [0, 5],
            "focus": [5, 20],
            "watch": [20, 40],
            "normal": [40, 100],
        },
    }
    return DemoData(
        reviewer_profiles=profiles,
        risk_tiers=risk_tiers,
        top_k=top_k,
        primary_policy=policy,
        validation_test=validation_test,
        feature_importance=_feature_importance(),
        group_importance=group_importance,
        feature_sets=feature_sets,
        split_summary=split_summary,
        model_metadata=metadata,
        risk_policy=policy_json,
    )

