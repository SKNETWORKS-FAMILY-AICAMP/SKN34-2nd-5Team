from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class DemoData:
    reviewer_profiles: pd.DataFrame
    top_k: pd.DataFrame
    primary_policy: pd.DataFrame
    validation_test: pd.DataFrame
    feature_importance: pd.DataFrame
    group_importance: pd.DataFrame
    feature_sets: pd.DataFrame
    split_summary: pd.DataFrame
    model_metadata: dict[str, Any]
    risk_policy: dict[str, Any]
    retention_distribution: pd.DataFrame
    multiclass_validation: pd.DataFrame
    multiclass_top_k: pd.DataFrame
    multiclass_confusion: pd.DataFrame


STATE_LABELS = {
    0: "파워 지위 유지",
    1: "파워 지위 약화",
    2: "리뷰 활동 중단",
}
STATE_NAMES = {0: "retained", 1: "weakened", 2: "stopped"}
CONFUSION = np.array(
    [
        [1_523, 924, 137],
        [711, 1_789, 565],
        [98, 325, 461],
    ]
)
SELECTED_ACTUAL_COUNTS = {0: 165, 1: 661, 2: 481}


def _state_pairs() -> tuple[np.ndarray, np.ndarray]:
    """Create anonymous states matching the validated v04 Test confusion matrix."""
    rng = np.random.default_rng(3405)
    selected: list[tuple[int, int]] = []
    remaining: list[tuple[int, int]] = []
    for actual in range(3):
        pairs = np.concatenate(
            [
                np.tile(np.array([[actual, predicted]], dtype="int8"), (users, 1))
                for predicted, users in enumerate(CONFUSION[actual])
            ]
        )
        rng.shuffle(pairs)
        cut = SELECTED_ACTUAL_COUNTS[actual]
        selected.extend(map(tuple, pairs[:cut]))
        remaining.extend(map(tuple, pairs[cut:]))
    rng.shuffle(selected)
    rng.shuffle(remaining)
    ordered = np.asarray([*selected, *remaining], dtype="int8")
    return ordered[:, 0], ordered[:, 1]


def _profile_frame() -> pd.DataFrame:
    total = 6_533
    selected_users = 1_307
    no_prior_users = 1_692
    rng = np.random.default_rng(3406)
    actual_states, predicted_states = _state_pairs()

    priority_score = np.linspace(0.98, 0.12, total)
    stopped_share = np.where(predicted_states == 2, 0.62, 0.30)
    stopped_score = priority_score * stopped_share
    weakened_score = priority_score - stopped_score

    recent_reviews = np.maximum(10, np.rint(rng.gamma(3.2, 4.4, total) + 9)).astype(int)
    recent_months = np.clip(np.rint(rng.normal(6.8, 1.8, total)), 3, 12).astype(int)
    recent_businesses = np.maximum(
        1,
        recent_reviews - rng.binomial(np.minimum(recent_reviews, 5), 0.18),
    )
    recent_recency = np.clip(rng.gamma(2.4, 28, total), 0, 365)
    recent_interval = np.clip(rng.normal(22, 10, total), 1, 180)

    prior_available = np.ones(total, dtype="int8")
    prior_available[:no_prior_users] = 0
    rng.shuffle(prior_available)
    has_prior = prior_available == 1

    baseline_reviews = np.zeros(total, dtype=int)
    baseline_months = np.zeros(total, dtype=int)
    baseline_businesses = np.zeros(total, dtype=int)
    baseline_recency = np.full(total, np.nan)
    baseline_interval = np.full(total, np.nan)
    baseline_reviews[has_prior] = np.maximum(
        1,
        np.rint(recent_reviews[has_prior] * rng.uniform(0.8, 1.8, has_prior.sum())),
    ).astype(int)
    baseline_months[has_prior] = np.clip(
        np.rint(recent_months[has_prior] * rng.uniform(0.8, 1.4, has_prior.sum())),
        1,
        12,
    ).astype(int)
    baseline_businesses[has_prior] = np.maximum(
        1,
        np.rint(recent_businesses[has_prior] * rng.uniform(0.8, 1.7, has_prior.sum())),
    ).astype(int)
    baseline_recency[has_prior] = np.clip(
        recent_recency[has_prior] + rng.normal(-10, 35, has_prior.sum()),
        0,
        365,
    )
    baseline_interval[has_prior] = np.clip(
        recent_interval[has_prior] + rng.normal(-4, 12, has_prior.sum()),
        1,
        180,
    )

    target_reviews = np.where(
        actual_states == 0,
        rng.integers(10, 30, total),
        np.where(actual_states == 1, rng.integers(1, 10, total), 0),
    )
    target_months = np.where(
        actual_states == 0,
        rng.integers(3, 10, total),
        np.where(actual_states == 1, rng.integers(1, 3, total), 0),
    )

    frame = pd.DataFrame(
        {
            "sample_id": [f"demo_reviewer_{rank:05d}_2018" for rank in range(1, total + 1)],
            "user_id": [f"demo_reviewer_{rank:05d}" for rank in range(1, total + 1)],
            "comparison_year": 2017,
            "selection_year": 2018,
            "target_year": 2019,
            "target_review_count": target_reviews,
            "target_active_months": target_months,
            "retention_state": actual_states,
            "churn": (actual_states == 2).astype("int8"),
            "prior_activity_available": prior_available,
            "scope": "익명 합성 데모",
            "baseline_review_count": baseline_reviews,
            "recent_review_count": recent_reviews,
            "baseline_active_months": baseline_months,
            "recent_active_months": recent_months,
            "baseline_unique_business_count": baseline_businesses,
            "recent_unique_business_count": recent_businesses,
            "baseline_recency_days": baseline_recency,
            "recent_recency_days": recent_recency,
            "baseline_mean_interval_days": baseline_interval,
            "recent_mean_interval_days": recent_interval,
            "retained_score": 1 - priority_score,
            "weakened_score": weakened_score,
            "stopped_score": stopped_score,
            "priority_score": priority_score,
            "predicted_state": predicted_states,
            "priority_rank": np.arange(1, total + 1),
            "priority_top_percent": np.arange(1, total + 1) / total * 100,
            "selected_for_crm": (
                np.arange(1, total + 1) <= selected_users
            ).astype("int8"),
        }
    )
    frame["retention_state_label"] = frame["retention_state"].map(STATE_LABELS)
    frame["predicted_state_label"] = frame["predicted_state"].map(STATE_LABELS)
    frame["risk_score"] = frame["priority_score"]
    frame["risk_rank"] = frame["priority_rank"]
    frame["risk_top_percent"] = frame["priority_top_percent"]
    frame["crm_target"] = frame["selected_for_crm"]
    frame["review_count_decline_rate"] = np.where(
        has_prior,
        1 - frame["recent_review_count"] / frame["baseline_review_count"],
        np.nan,
    )
    frame["active_month_decline_rate"] = np.where(
        has_prior,
        1 - frame["recent_active_months"] / frame["baseline_active_months"],
        np.nan,
    )
    frame["unique_business_decline_rate"] = np.where(
        has_prior,
        1
        - frame["recent_unique_business_count"]
        / frame["baseline_unique_business_count"],
        np.nan,
    )
    frame["recency_increase_days"] = (
        frame["recent_recency_days"] - frame["baseline_recency_days"]
    )
    frame["mean_interval_increase_days"] = (
        frame["recent_mean_interval_days"] - frame["baseline_mean_interval_days"]
    )
    return frame


def _validation() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "record_type": "final_test",
                "split": "selection_2018_target_2019",
                "train_selection_years": "2010~2017",
                "validation_selection_year": 2018,
                "train_samples": 31_420,
                "validation_samples": 6_533,
                "accuracy": 0.5775294658,
                "balanced_accuracy": 0.5648587613,
                "macro_precision": 0.5461167960,
                "macro_recall": 0.5648587613,
                "macro_f1": 0.5520979095,
                "weighted_f1": 0.5810733959,
                "macro_pr_auc": 0.5792363193,
                "macro_ovr_roc_auc": 0.7560738477,
                "retained_precision": 0.6530874786,
                "retained_recall": 0.5893962848,
                "retained_f1": 0.6196094386,
                "weakened_precision": 0.5888742594,
                "weakened_recall": 0.5836867863,
                "weakened_f1": 0.5862690480,
                "stopped_precision": 0.3963886500,
                "stopped_recall": 0.5214932127,
                "stopped_f1": 0.4504152418,
            }
        ]
    )


def _top_k() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "split": "final_test",
                "ranking": "unified",
                "target_rate": 0.20,
                "target_users": 1_307,
                "status_loss_captured": 1_142,
                "status_loss_precision": 0.8737566947,
                "status_loss_recall": 0.2891871360,
                "status_loss_lift": 1.4454931594,
                "stopped_captured": 481,
                "stopped_recall": 0.5441176471,
                "weakened_captured": 661,
                "weakened_recall": 0.2156606852,
            }
        ]
    )


def _confusion() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "split": "final_test",
                "actual_state": STATE_NAMES[actual],
                "predicted_state": STATE_NAMES[predicted],
                "users": int(CONFUSION[actual, predicted]),
            }
            for actual in range(3)
            for predicted in range(3)
        ]
    )


def build_demo_data() -> DemoData:
    profiles = _profile_frame()
    metadata = {
        "version": "v04",
        "model_name": "Core Multiclass Logistic v04 · 익명 합성 데모",
        "feature_count": 43,
        "test_selection_year": 2018,
        "test_target_year": 2019,
        "test_samples": 6_533,
        "test_metrics": {"macro_pr_auc": 0.5792363193},
        "priority_policy": {
            "score": "weakened_score + stopped_score",
            "primary_target_rate": 0.20,
        },
        "score_warning": (
            "클래스별 점수는 확률 보정 전 모델 점수이며 실제 상태 확률로 "
            "표현하지 않는다."
        ),
    }
    retention_distribution = pd.DataFrame(
        [
            (2018, 2019, state, STATE_LABELS[state], int((profiles["retention_state"] == state).sum()))
            for state in range(3)
        ],
        columns=[
            "selection_year",
            "target_year",
            "retention_state",
            "retention_state_label",
            "users",
        ],
    )
    return DemoData(
        reviewer_profiles=profiles,
        top_k=pd.DataFrame(),
        primary_policy=pd.DataFrame(),
        validation_test=pd.DataFrame(),
        feature_importance=pd.DataFrame(),
        group_importance=pd.DataFrame(),
        feature_sets=pd.DataFrame(),
        split_summary=pd.DataFrame(),
        model_metadata=metadata,
        risk_policy={
            "version": "v04",
            "primary_policy": "unified_top_20_percent",
        },
        retention_distribution=retention_distribution,
        multiclass_validation=_validation(),
        multiclass_top_k=_top_k(),
        multiclass_confusion=_confusion(),
    )
