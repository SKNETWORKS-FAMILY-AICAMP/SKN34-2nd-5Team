"""Export v04 project data as JSON for the React frontend.

React has no API yet, so it reads static JSON instead of hitting FastAPI/MySQL.
This script reuses the Streamlit app's own `core` modules so the exported
values go through exactly the same derivation logic the Streamlit screens use —
reimplementing that logic in JavaScript would let the two apps drift apart.

Run from the repository root:

    ./venv/Scripts/python.exe scripts/export_frontend_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "archive" / "app_streamlit_v04"
OUT_DIR = ROOT / "app" / "src" / "data"
PUBLIC_DIR = ROOT / "app" / "public" / "data"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core.data import load_app_data  # noqa: E402
from core.formatters import days, percent, signed_phrase  # noqa: E402
from core.insights import (  # noqa: E402
    DECISION_PLAYBOOKS,
    STATE_RECOMMENDATIONS,
    DECISION_STATE_MAP,
    SIGNAL_LABELS,
    STRATEGIES,
    risk_signals,
    strategy_for,
)

# `feature_group_label` in the report CSVs is written in cp949 and comes back
# mojibake, so map the stable ascii group key to its Korean label here instead.
FEATURE_GROUP_LABELS = {
    "interval": "작성 간격",
    "activity": "리뷰 활동량",
    "business": "음식점 탐색",
}

STATE_KEYS = {0: "retained", 1: "weakened", 2: "stopped"}


def _f(value, default: float = 0.0) -> float:
    """Coerce to a JSON-safe float (NaN/inf are not valid JSON)."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if pd.isna(numeric) or numeric in (float("inf"), float("-inf")):
        return default
    return numeric


def _i(value, default: int = 0) -> int:
    return int(_f(value, default))


def build_change_text(row: pd.Series) -> str:
    """Mirror the one-line "핵심 변화" summary in views/operation_home.py.

    The queue always phrases the change in review counts — picking whichever
    metric moved most would read better but would not match the Streamlit copy.
    """
    if not bool(row.get("prior_activity_available", 1)):
        comparison_year = _i(row.get("comparison_year"), 2017)
        return f"{comparison_year}년 비교 활동 없음 · 전년도 대비 변화율 계산 불가"

    return (
        f"리뷰 수 {_i(row.get('baseline_review_count'))}건 → "
        f"{_i(row.get('recent_review_count'))}건 · "
        + signed_phrase(
            row.get("review_count_decline_rate"),
            percent,
            when_positive="감소",
            when_negative="증가",
        )
    )


def build_row(row: pd.Series) -> dict:
    prior_available = bool(row.get("prior_activity_available", 1))
    comparison_year = _i(row.get("comparison_year"), 2017)
    no_comparison = f"{comparison_year}년 비교 활동 없음 · 전년도 대비 변화율 계산 불가"
    strategy = strategy_for(row)
    signals = risk_signals(row)

    def delta(value, formatter, positive: str, negative: str) -> str:
        if not prior_available:
            return no_comparison
        return signed_phrase(
            value, formatter, when_positive=positive, when_negative=negative
        )

    return {
        "userId": str(row["user_id"]),
        "sampleId": str(row["sample_id"]),
        "priorityRank": _i(row.get("priority_rank")),
        "priorityTopPercent": _f(row.get("priority_top_percent")),
        "priorityScore": _f(row.get("priority_score")),
        "modelJudgment": str(row.get("model_judgment", "")),
        "riskType": str(row.get("risk_type", "")),
        "coreSignal": str(row.get("core_signal", "")),
        "coreChange": build_change_text(row),
        "recommendedReview": strategy["primary"],
        "recommendedDecision": DECISION_STATE_MAP.get(
            _i(row.get("predicted_state")), "변화 지켜보기"
        ),
        "crmTarget": bool(row.get("crm_target", 0)),
        "crmTargetLabel": str(row.get("crm_target_label", "")),
        "priorActivityAvailable": prior_available,
        "comparisonYear": comparison_year,
        "selectionYear": _i(row.get("selection_year"), 2018),
        "targetYear": _i(row.get("target_year"), 2019),
        "scores": {
            "retained": _f(row.get("retained_score")),
            "weakened": _f(row.get("weakened_score")),
            "stopped": _f(row.get("stopped_score")),
        },
        "recentActiveMonths": _i(row.get("recent_active_months")),
        "recentRecencyDays": _f(row.get("recent_recency_days")),
        "reviewCountDeclineRate": _f(row.get("review_count_decline_rate")),
        "activeMonthDeclineRate": _f(row.get("active_month_decline_rate")),
        # The worklist "핵심 변화" column shows the 2 strongest signals
        # (views/risk_queue.py); the rest of the evidence lives in the detail file.
        "metrics": [signal.evidence for signal in signals[:2]],
    }


def build_detail(row: pd.Series) -> dict:
    """Fields only the Reviewer 360 screen needs, split out to keep the bundle small."""
    prior_available = bool(row.get("prior_activity_available", 1))
    comparison_year = _i(row.get("comparison_year"), 2017)
    no_comparison = f"{comparison_year}년 비교 활동 없음 · 전년도 대비 변화율 계산 불가"
    signals = risk_signals(row)

    def delta(value, formatter, positive: str, negative: str) -> str:
        if not prior_available:
            return no_comparison
        return signed_phrase(
            value, formatter, when_positive=positive, when_negative=negative
        )

    return {
        # "활동 변화 요약" grouped bar chart (Streamlit profile_activity)
        "activitySummary": [
            {
                "label": "리뷰 수",
                "before": _i(row.get("baseline_review_count")),
                "after": _i(row.get("recent_review_count")),
            },
            {
                "label": "활동 월",
                "before": _i(row.get("baseline_active_months")),
                "after": _i(row.get("recent_active_months")),
            },
            {
                "label": "고유 음식점",
                "before": _i(row.get("baseline_unique_business_count")),
                "after": _i(row.get("recent_unique_business_count")),
            },
        ],
        # "작성 주기 변화" chart (Streamlit interval_comparison)
        "intervalComparison": [
            {
                "label": "평균 작성 간격",
                "before": _f(row.get("baseline_mean_interval_days")),
                "after": _f(row.get("recent_mean_interval_days")),
            },
            {
                "label": "마지막 리뷰 공백",
                "before": _f(row.get("baseline_recency_days")),
                "after": _f(row.get("recent_recency_days")),
            },
        ],
        # "활동이 이렇게 변했습니다" tiles (Streamlit change_story)
        "changes": [
            {
                "label": "리뷰 수",
                "before": (
                    f"{_i(row.get('baseline_review_count'))}건"
                    if prior_available
                    else f"{comparison_year}년 비교 활동 없음"
                ),
                "after": f"{_i(row.get('recent_review_count'))}건",
                "delta": delta(
                    row.get("review_count_decline_rate"), percent, "감소", "증가"
                ),
                "tone": (
                    "muted"
                    if not prior_available
                    else (
                        "warning"
                        if _f(row.get("review_count_decline_rate")) >= 0
                        else "positive"
                    )
                ),
            },
            {
                "label": "활동 월",
                "before": (
                    f"{_i(row.get('baseline_active_months'))}개월"
                    if prior_available
                    else f"{comparison_year}년 비교 활동 없음"
                ),
                "after": f"{_i(row.get('recent_active_months'))}개월",
                "delta": delta(
                    row.get("active_month_decline_rate"), percent, "감소", "증가"
                ),
                "tone": (
                    "muted"
                    if not prior_available
                    else (
                        "warning"
                        if _f(row.get("active_month_decline_rate")) >= 0
                        else "positive"
                    )
                ),
            },
            {
                "label": "고유 음식점",
                "before": (
                    f"{_i(row.get('baseline_unique_business_count'))}곳"
                    if prior_available
                    else f"{comparison_year}년 비교 활동 없음"
                ),
                "after": f"{_i(row.get('recent_unique_business_count'))}곳",
                "delta": delta(
                    row.get("unique_business_decline_rate"), percent, "감소", "증가"
                ),
                "tone": (
                    "muted"
                    if not prior_available
                    else (
                        "warning"
                        if _f(row.get("unique_business_decline_rate")) >= 0
                        else "positive"
                    )
                ),
            },
            {
                "label": "리뷰 공백",
                "before": (
                    days(row.get("baseline_recency_days"))
                    if prior_available
                    else f"{comparison_year}년 비교 활동 없음"
                ),
                "after": days(row.get("recent_recency_days")),
                "delta": (
                    f"{_f(row.get('recency_increase_days')):+.0f}일"
                    if prior_available
                    else no_comparison
                ),
                "tone": (
                    "muted"
                    if not prior_available
                    else (
                        "positive"
                        if _f(row.get("recency_increase_days")) < 0
                        else "warning"
                    )
                ),
            },
        ],
        # Streamlit shows the 3 strongest signals, ordered by severity.
        "evidence": [
            {"title": signal.name, "evidence": signal.evidence, "group": signal.group}
            for signal in signals[:3]
        ],
        # strategy is a pure function of (predicted_state, risk_type); the two
        # lookup tables ship once in strategies.json rather than per reviewer.
        "predictedState": _i(row.get("predicted_state")),
        # Post-hoc validation, hidden behind the disclosure toggle in the UI.
        "actual": {
            "state": str(row.get("retention_state_label", "—")),
            "targetReviewCount": _i(row.get("target_review_count")),
            "targetActiveMonths": _i(row.get("target_active_months")),
        },
    }


def export_operations(data, profiles: pd.DataFrame) -> dict:
    policy = (
        data.primary_policy.iloc[0] if not data.primary_policy.empty else pd.Series()
    )
    target_users = _i(policy.get("target_users"), int(profiles["crm_target"].sum()))
    captured = _i(policy.get("status_loss_captured"))
    recall = _f(policy.get("status_loss_recall"))
    counts = profiles["predicted_state"].value_counts()

    return {
        "modelVersion": str(data.model_version),
        "dataMode": str(data.data_mode),
        "snapshot": f"Test {data.target_year}",
        "targetYear": _i(data.target_year, 2019),
        "totalReviewers": int(len(profiles)),
        "targetUsers": target_users,
        "capturedUsers": captured,
        "precision": _f(policy.get("status_loss_precision")),
        "recall": recall,
        "lift": _f(policy.get("status_loss_lift")),
        "recallCeiling": (target_users / (captured / recall)) if recall else 0.0,
        "retainedUsers": int(counts.get(0, 0)),
        "weakenedUsers": int(counts.get(1, 0)),
        "stoppedUsers": int(counts.get(2, 0)),
    }


def _read_table(name: str) -> pd.DataFrame:
    path = ROOT / "reports" / "tables" / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _final_multiclass_row(validation: pd.DataFrame) -> pd.Series:
    if validation.empty:
        return pd.Series(dtype="float64")
    finals = validation.loc[validation["record_type"].eq("final_test")]
    return finals.iloc[0] if not finals.empty else validation.iloc[-1]


def _multiclass_class_performance(row: pd.Series) -> list[dict]:
    return [
        {
            "className": label,
            "precision": _f(row.get(f"{key}_precision")),
            "recall": _f(row.get(f"{key}_recall")),
            "f1": _f(row.get(f"{key}_f1")),
            "prAuc": _f(row.get(f"{key}_pr_auc")),
            "support": _i(row.get(f"{key}_support")),
        }
        for key, label in [
            ("retained", "파워 지위 유지"),
            ("weakened", "파워 지위 약화"),
            ("stopped", "리뷰 활동 중단"),
        ]
    ]


def _multiclass_confusion(confusion: pd.DataFrame) -> list[dict]:
    if confusion.empty:
        return []
    final_confusion = confusion.loc[confusion["split"].eq("final_test")]
    if final_confusion.empty:
        final_confusion = confusion.loc[
            confusion["split"].eq(confusion["split"].iloc[-1])
        ]
    return [
        {
            "actual": str(row["actual_state"]),
            "predicted": str(row["predicted_state"]),
            "users": _i(row["users"]),
        }
        for _, row in final_confusion.iterrows()
    ]


def _multiclass_top_k(top_k: pd.DataFrame) -> list[dict]:
    if top_k.empty:
        return []
    unified = (
        top_k.loc[top_k["ranking"].eq("unified")] if "ranking" in top_k else top_k
    )
    final_top_k = unified.loc[unified["split"].eq("final_test")]
    if final_top_k.empty:
        final_top_k = unified.loc[unified["split"].eq(unified["split"].iloc[0])]
    return [
        {
            "targetRate": _f(row.get("target_rate")),
            "targetUsers": _i(row.get("target_users")),
            "captured": _i(row.get("status_loss_captured")),
            "precision": _f(row.get("status_loss_precision")),
            "recall": _f(row.get("status_loss_recall")),
            "lift": _f(row.get("status_loss_lift")),
        }
        for _, row in final_top_k.iterrows()
    ]


def _feature_importance(features: pd.DataFrame) -> list[dict]:
    if features.empty:
        return []
    return [
        {
            "rank": _i(row.get("rank")),
            "feature": str(row.get("feature")),
            "group": FEATURE_GROUP_LABELS.get(
                str(row.get("feature_group")), str(row.get("feature_group"))
            ),
            "importance": _f(row.get("importance_mean")),
            "sharePercent": _f(row.get("importance_share_pct")),
        }
        for _, row in features.head(15).iterrows()
    ]


def _group_importance(groups: pd.DataFrame) -> list[dict]:
    if groups.empty:
        return []
    return [
        {
            "group": FEATURE_GROUP_LABELS.get(
                str(row.get("feature_group")), str(row.get("feature_group"))
            ),
            "featureCount": _i(row.get("feature_count")),
            "importance": _f(row.get("importance_mean")),
            "rank": _i(row.get("rank")),
        }
        for _, row in groups.iterrows()
    ]


def _multiclass_trust_block(
    validation: pd.DataFrame,
    top_k: pd.DataFrame,
    confusion: pd.DataFrame,
    features: pd.DataFrame,
    groups: pd.DataFrame,
) -> dict:
    """One 3-class model's trust numbers — shared by v04 (main) and the v03
    comparison block in views/trust_center.py, which is the same report shape
    from an earlier cohort.
    """
    row = _final_multiclass_row(validation)
    return {
        "available": not validation.empty,
        "validationSamples": _i(row.get("validation_samples")),
        "overall": {
            "macroF1": _f(row.get("macro_f1")),
            "macroPrAuc": _f(row.get("macro_pr_auc")),
            "macroRocAuc": _f(row.get("macro_ovr_roc_auc")),
            "balancedAccuracy": _f(row.get("balanced_accuracy")),
            "accuracy": _f(row.get("accuracy")),
        },
        "classPerformance": _multiclass_class_performance(row),
        "confusionMatrix": _multiclass_confusion(confusion),
        "topK": _multiclass_top_k(top_k),
        "featureImportance": _feature_importance(features),
        "groupImportance": _group_importance(groups),
    }


def _v03_top20(top_k: pd.DataFrame) -> dict | None:
    """The 상위 20% metric strip shown above the v03 expander's Top-K chart
    (views/trust_center.py:202-231) — trust_center.py's own historical
    reference point, not the v04 operating policy.
    """
    if top_k.empty:
        return None
    match = top_k.loc[
        top_k["split"].eq("final_test")
        & top_k["ranking"].eq("unified")
        & top_k["target_rate"].eq(0.20)
    ]
    if match.empty:
        return None
    row = match.iloc[0]
    return {
        "targetUsers": _i(row.get("target_users")),
        "captured": _i(row.get("status_loss_captured")),
        "precision": _f(row.get("status_loss_precision")),
        "recall": _f(row.get("status_loss_recall")),
        "lift": _f(row.get("status_loss_lift")),
    }


def _v02_block() -> dict:
    """v02 is an earlier-generation binary churn model, not a 3-class model,
    so its metrics/top-k schema differs from v03/v04 (views/trust_center.py
    lines 233-301).
    """
    validation_test = _read_table("validation_test_comparison_v02")
    test_row = None
    if not validation_test.empty:
        test = validation_test.loc[
            validation_test["dataset"].astype(str).str.lower().eq("test")
        ]
        test_row = (test.iloc[0] if not test.empty else validation_test.iloc[-1]).to_dict()

    top_k = _read_table("final_test_top_k_performance_v02")
    features = _read_table("final_feature_importance_v02")
    groups = _read_table("final_feature_group_importance_v02")

    return {
        "available": not validation_test.empty or not top_k.empty,
        "overall": {
            "precision": _f((test_row or {}).get("precision")),
            "recall": _f((test_row or {}).get("recall")),
            "rocAuc": _f((test_row or {}).get("roc_auc")),
            "prAuc": _f((test_row or {}).get("pr_auc")),
        },
        "datasetComparison": [
            {
                "dataset": str(row["dataset"]),
                "precision": _f(row.get("precision")),
                "recall": _f(row.get("recall")),
                "f1": _f(row.get("f1")),
                "rocAuc": _f(row.get("roc_auc")),
                "prAuc": _f(row.get("pr_auc")),
            }
            for _, row in validation_test.iterrows()
        ],
        "topK": [
            {
                "targetRatePercent": _f(row.get("target_rate_pct")),
                "targetUsers": _i(row.get("target_users")),
                "capturedChurnUsers": _i(row.get("captured_churn_users")),
                "precision": _f(row.get("precision_at_k")),
                "recall": _f(row.get("recall_at_k")),
                "lift": _f(row.get("lift_at_k")),
            }
            for _, row in top_k.iterrows()
        ],
        "featureImportance": _feature_importance(features),
        "groupImportance": _group_importance(groups),
    }


def export_trust(data) -> dict:
    v04_validation = _read_table("multiclass_validation_results_v04")
    v04_top_k = _read_table("multiclass_top_k_performance_v04")
    v04_confusion = _read_table("multiclass_confusion_matrix_v04")
    v04_features = _read_table("final_feature_importance_v04")
    v04_groups = _read_table("final_feature_group_importance_v04")

    v04 = _multiclass_trust_block(
        v04_validation, v04_top_k, v04_confusion, v04_features, v04_groups
    )

    v03_top_k = _read_table("multiclass_top_k_performance_v03")
    v03 = _multiclass_trust_block(
        _read_table("multiclass_validation_results_v03"),
        v03_top_k,
        _read_table("multiclass_confusion_matrix_v03"),
        _read_table("final_feature_importance_v03"),
        _read_table("final_feature_group_importance_v03"),
    )
    v03["top20"] = _v03_top20(v03_top_k)

    return {
        "modelVersion": str(data.model_version),
        "validationPeriod": f"Test {data.target_year}",
        "overall": v04["overall"],
        "classPerformance": v04["classPerformance"],
        "confusionMatrix": v04["confusionMatrix"],
        "topK": v04["topK"],
        "featureImportance": v04["featureImportance"],
        "groupImportance": v04["groupImportance"],
        "baselinePrAuc": _f(
            v04_features["baseline_pr_auc"].iloc[0] if not v04_features.empty else 0.0
        ),
        # Reference-only comparisons against earlier model generations, shown
        # collapsed in Streamlit (views/trust_center.py) so they never mix
        # with the v04 numbers above.
        "v03": v03,
        "v02": _v02_block(),
    }


def export_strategies() -> dict:
    """Lookup tables the detail screen combines into a reviewer's strategy.

    Mirrors core.insights.strategy_for: the title and summary come from the
    predicted state, the secondary action and channel from the risk type.
    """
    return {
        "byState": {
            str(state): {
                "title": STATE_RECOMMENDATIONS[state]["primary"],
                "description": STATE_RECOMMENDATIONS[state]["summary"],
            }
            for state in (0, 1, 2)
        },
        "byRiskType": {
            risk_type: {
                "secondary": entry["secondary"],
                "channel": entry["channel"],
            }
            for risk_type, entry in STRATEGIES.items()
        },
    }


def export_playbooks() -> list[dict]:
    """DECISION_PLAYBOOKS keyed by manager decision (DEC-011).

    These are rule-based operating drafts, not interventions with measured
    effect, and the screen has to keep saying so.
    """
    return [
        {
            "decision": decision,
            "condition": entry["condition"],
            "signals": entry["signals"],
            "primaryAction": entry["primary_action"],
            "subStrategy": [
                {"riskType": risk_type, "text": text}
                for risk_type, text in entry["sub_strategy"].items()
            ],
            "channel": entry["channel"],
            "needsUpgrade": entry["needs_upgrade"],
            "successDraft": entry["success_draft"],
            "modelJudgment": next(
                (
                    judgment
                    for state, judgment in [
                        (0, "유지 우세"),
                        (1, "약화 우세"),
                        (2, "중단 우세"),
                    ]
                    if DECISION_STATE_MAP[state] == decision
                ),
                None,
            ),
        }
        for decision, entry in DECISION_PLAYBOOKS.items()
    ]


def _load_all_reviews() -> pd.DataFrame:
    """restaurant_reviews.parquet alone undercounts — pipeline/v04/preprocessing.py
    unions it with a second reviews file (there as additional_culinary_reviews_v02.parquet
    here) to build baseline_review_count/recent_review_count. Skipping that union
    left review-count derivations short for 63% of reviewers (mean gap ~2,
    max 40) versus the profile's own counts — verified against
    final_test_retention_profiles_v04.parquet before wiring this in.
    """
    paths = [
        ROOT / "data" / "interim" / "restaurant_reviews.parquet",
        ROOT / "data" / "interim" / "additional_culinary_reviews_v02.parquet",
    ]
    frames = [
        pd.read_parquet(path, columns=["user_id", "business_id", "date"])
        for path in paths
        if path.exists()
    ]
    if not frames:
        return pd.DataFrame(columns=["user_id", "business_id", "date"])
    return pd.concat(frames, ignore_index=True)


def export_monthly_activity(profiles: pd.DataFrame) -> dict[str, list[dict]]:
    """Per-reviewer monthly review count + unique business count, derived from
    raw reviews rather than waiting on reviewer_monthly_activity_v01.parquet.

    That contract file does not exist in this repo, so Streamlit's own
    reviewer_360.py (lines 278-294) falls back to an empty state for the same
    reason — this derivation only fills the gap on the React side (Streamlit
    is left untouched, decision 2026-07-28).

    Restricted to comparison_year..selection_year — the model's actual feature
    window — and never target_year, so this tab (not gated behind the "검증
    정답 표시" toggle) can't leak the post-hoc validation outcome.
    """
    if profiles.empty:
        return {}

    cohort = profiles.copy()
    cohort["user_id"] = cohort["user_id"].astype(str)
    comparison_year = _i(cohort["comparison_year"].iloc[0], 2017)
    selection_year = _i(cohort["selection_year"].iloc[0], 2018)

    reviews = _load_all_reviews()
    if reviews.empty:
        return {}
    reviews["user_id"] = reviews["user_id"].astype(str)
    reviews = reviews[reviews["user_id"].isin(cohort["user_id"])]
    reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")
    reviews = reviews[reviews["date"].dt.year.between(comparison_year, selection_year)]
    reviews["month"] = reviews["date"].dt.strftime("%Y-%m")

    grouped = (
        reviews.groupby(["user_id", "month"])
        .agg(
            reviewCount=("business_id", "size"),
            uniqueBusinessCount=("business_id", "nunique"),
        )
        .reset_index()
        .sort_values(["user_id", "month"])
    )

    result: dict[str, list[dict]] = {}
    for user_id, group in grouped.groupby("user_id"):
        result[user_id] = [
            {
                "month": row.month,
                "reviewCount": int(row.reviewCount),
                "uniqueBusinessCount": int(row.uniqueBusinessCount),
            }
            for row in group.itertuples()
        ]
    return result


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:,.0f} KB)")


def main() -> None:
    data = load_app_data()
    profiles = data.reviewer_profiles

    if profiles.empty:
        raise SystemExit("reviewer_profiles is empty. Check the v04 data files.")

    print(f"loaded {len(profiles):,} reviewer profiles (mode={data.data_mode})")

    ordered = profiles.sort_values("priority_rank")

    # Worklist rows are bundled; per-reviewer detail is served from public/ and
    # fetched only when a Reviewer 360 screen opens, so the whole cohort stays
    # browsable without a multi-megabyte bundle.
    write(OUT_DIR / "operations.json", export_operations(data, profiles))
    write(OUT_DIR / "trust.json", export_trust(data))
    write(OUT_DIR / "playbooks.json", export_playbooks())
    write(OUT_DIR / "strategies.json", export_strategies())
    write(OUT_DIR / "regional.json", export_regional(profiles))
    write(OUT_DIR / "reviewers.json", [build_row(row) for _, row in ordered.iterrows()])

    monthly_activity = export_monthly_activity(profiles)
    details = {}
    for _, row in ordered.iterrows():
        user_id = str(row["user_id"])
        detail = build_detail(row)
        detail["monthlyActivity"] = monthly_activity.get(user_id, [])
        details[user_id] = detail
    write(PUBLIC_DIR / "reviewer-details.json", details)

    print(f"exported {len(ordered):,} reviewers")



def export_regional(profiles: pd.DataFrame) -> dict:
    """Aggregate content-supply risk by 권역 (the reviewer's most-reviewed state).

    DEC/regional_risk.py refuses to show invented numbers, so this is built from
    the actual review-to-business join rather than a placeholder table:

    - 지역 정의: the state a reviewer wrote about most during the feature window,
      so suburbs fold into their metro instead of splitting into 200+ cities.
      This is review activity, never a claim about where the reviewer lives.
    - 표본 기준: regions below MINIMUM_REVIEWERS are reported separately instead
      of being ranked, because a handful of reviewers makes the rate meaningless.
    """
    minimum_reviewers = 30

    business_path = ROOT / "data" / "interim" / "restaurant_businesses.parquet"

    reviews = _load_all_reviews()
    if reviews.empty or not business_path.exists():
        return {"available": False, "regions": [], "minimumReviewers": minimum_reviewers}

    cohort = profiles.copy()
    cohort["user_id"] = cohort["user_id"].astype(str)
    cohort = cohort.set_index("user_id")

    selection_year = _i(cohort["selection_year"].iloc[0], 2018)
    comparison_year = _i(cohort["comparison_year"].iloc[0], 2017)

    reviews["user_id"] = reviews["user_id"].astype(str)
    reviews = reviews[reviews["user_id"].isin(cohort.index)]
    reviews["year"] = pd.to_datetime(reviews["date"], errors="coerce").dt.year
    window = reviews[
        reviews["year"].between(comparison_year, selection_year)
    ]

    businesses = pd.read_parquet(
        business_path, columns=["business_id", "city", "state"]
    )
    joined = window.merge(businesses, on="business_id", how="left").dropna(
        subset=["state"]
    )

    # One region per reviewer: where they reviewed most in the window.
    per_user = (
        joined.groupby(["user_id", "state"])
        .size()
        .reset_index(name="reviews")
        .sort_values("reviews", ascending=False)
        .drop_duplicates("user_id")
    )
    per_user = per_user.join(
        cohort[["predicted_state", "crm_target"]],
        on="user_id",
    )

    # Label each region by the city most of its reviewers write about.
    top_city = (
        joined.groupby(["user_id", "state", "city"])
        .size()
        .reset_index(name="reviews")
        .sort_values("reviews", ascending=False)
        .drop_duplicates("user_id")
        .groupby(["state", "city"])
        .size()
        .reset_index(name="reviewers")
        .sort_values("reviewers", ascending=False)
        .drop_duplicates("state")
        .set_index("state")["city"]
    )

    regions = []
    for state, group in per_user.groupby("state"):
        reviewers = int(len(group))
        weakened = int((group["predicted_state"] == 1).sum())
        stopped = int((group["predicted_state"] == 2).sum())
        high_risk = weakened + stopped

        regions.append(
            {
                "region": str(state),
                "topCity": str(top_city.get(state, "—")),
                "reviewers": reviewers,
                "retained": int((group["predicted_state"] == 0).sum()),
                "weakened": weakened,
                "stopped": stopped,
                "highRisk": high_risk,
                "highRiskRate": high_risk / reviewers if reviewers else 0.0,
                "crmTargets": int(group["crm_target"].sum()),
                "belowMinimum": reviewers < minimum_reviewers,
            }
        )

    regions.sort(key=lambda item: item["reviewers"], reverse=True)

    return {
        "available": True,
        "minimumReviewers": minimum_reviewers,
        "comparisonYear": comparison_year,
        "selectionYear": selection_year,
        "coveredReviewers": int(len(per_user)),
        "totalReviewers": int(len(cohort)),
        "regions": regions,
    }

if __name__ == "__main__":
    main()
