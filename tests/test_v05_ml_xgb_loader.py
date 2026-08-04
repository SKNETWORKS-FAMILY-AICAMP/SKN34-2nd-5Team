from __future__ import annotations

import math

import pandas as pd

from database.load.load_v05_ml_xgb import (
    MODEL_VERSION,
    derive_feature_group_importance,
    sanitize_json,
)


def test_sanitize_json_replaces_non_finite_values() -> None:
    result = sanitize_json(
        {
            "missing": float("nan"),
            "positive_infinity": float("inf"),
            "nested": [1.0, float("-inf")],
        }
    )

    assert result == {
        "missing": None,
        "positive_infinity": None,
        "nested": [1.0, None],
    }


def test_derive_feature_group_importance_sums_single_feature_results() -> None:
    features = pd.DataFrame(
        [
            {
                "model_version": MODEL_VERSION,
                "split": "final_test",
                "feature_group": "activity",
                "feature_group_label": "리뷰 활동량",
                "importance_mean": 0.20,
                "importance_std": 0.03,
                "baseline_pr_auc": 0.58,
                "metric": "macro_pr_auc",
                "repeats": 20,
            },
            {
                "model_version": MODEL_VERSION,
                "split": "final_test",
                "feature_group": "activity",
                "feature_group_label": "리뷰 활동량",
                "importance_mean": 0.10,
                "importance_std": 0.04,
                "baseline_pr_auc": 0.58,
                "metric": "macro_pr_auc",
                "repeats": 20,
            },
            {
                "model_version": MODEL_VERSION,
                "split": "final_test",
                "feature_group": "business",
                "feature_group_label": "음식점 탐색",
                "importance_mean": 0.05,
                "importance_std": 0.01,
                "baseline_pr_auc": 0.58,
                "metric": "macro_pr_auc",
                "repeats": 20,
            },
        ]
    )

    result = derive_feature_group_importance(features)

    assert result["feature_group"].tolist() == ["activity", "business"]
    assert result["rank_no"].tolist() == [1, 2]
    assert result["feature_count"].tolist() == [2, 1]
    assert math.isclose(result.iloc[0]["importance_mean"], 0.30)
    assert math.isclose(result.iloc[0]["importance_std"], 0.05)
    assert set(result["method"]) == {"sum_single_feature_permutation"}
