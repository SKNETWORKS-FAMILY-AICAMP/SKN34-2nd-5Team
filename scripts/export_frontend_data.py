"""Export v04 project data as JSON for the React frontend.

React has no API yet, so it reads static JSON instead of hitting FastAPI/MySQL.
This script reuses the Streamlit app's own `core` modules so the exported
values go through exactly the same derivation logic the Streamlit screens use —
reimplementing that logic in JavaScript would let the two apps drift apart.

2026-07-30 update: React now reads through FastAPI/MySQL at runtime. The JSON
files this script produces remain as parity-reference and recovery artifacts;
they are not an automatic runtime fallback when an API request fails.

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
REVIEWER_REGION_PATH = (
    ROOT / "data" / "processed" / "reviewer_region_v04.parquet"
)
MONTHLY_ACTIVITY_PATH = (
    ROOT / "data" / "processed" / "reviewer_monthly_activity_v04.parquet"
)

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# core.data(=load_app_data)는 main() 안에서 지연 import한다 — 이 모듈을
# 그냥 import(예: api/에서 build_row/build_detail만 재사용)하는 것만으로
# streamlit이 딸려 들어오는 걸 막기 위해서다. 아래 shared.retention은
# streamlit 의존이 없는 순수 모듈이라 최상단에서 바로 가져와도 안전하다.
from shared.retention.formatters import days, percent, signed_phrase  # noqa: E402
from shared.retention.insights import (  # noqa: E402
    DECISION_PLAYBOOKS,
    STATE_RECOMMENDATIONS,
    DECISION_STATE_MAP,
    SIGNAL_LABELS,
    STRATEGIES,
    risk_signals,
    strategy_for,
)
from shared.retention.frontend_serializer import (  # noqa: E402
    _f,
    _i,
    build_change_text,
    build_row,
    build_detail,
)
from pipeline.v04.derived_reviewer_activity import (  # noqa: E402
    MONTHLY_COLUMNS,
    REGION_COLUMNS,
    validate_outputs,
)

# `feature_group_label` in the report CSVs is written in cp949 and comes back
# mojibake, so map the stable ascii group key to its Korean label here instead.
FEATURE_GROUP_LABELS = {
    "interval": "작성 간격",
    "activity": "리뷰 활동량",
    "business": "음식점 탐색",
}

STATE_KEYS = {0: "retained", 1: "weakened", 2: "stopped"}


# _f/_i/build_change_text/build_row/build_detail은
# shared/retention/frontend_serializer.py로 옮겼다 (top-level import).


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


def load_derived_reviewer_data(
    profiles: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and validate pipeline-owned artifacts before frontend export."""
    missing = [
        str(path)
        for path in [REVIEWER_REGION_PATH, MONTHLY_ACTIVITY_PATH]
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "React 파생 데이터 파일이 없습니다:\n- "
            + "\n- ".join(missing)
            + "\n먼저 다음 명령을 실행하세요:\n"
            + r".\.venv\Scripts\python.exe "
            + r"pipeline\v04\derived_reviewer_activity.py"
        )

    reviewer_region = pd.read_parquet(
        REVIEWER_REGION_PATH,
        columns=REGION_COLUMNS,
    )
    monthly_activity = pd.read_parquet(
        MONTHLY_ACTIVITY_PATH,
        columns=MONTHLY_COLUMNS,
    )
    validate_outputs(
        profiles,
        reviewer_region,
        monthly_activity,
        expected_profile_rows=len(profiles),
    )
    return reviewer_region, monthly_activity


def export_monthly_activity(
    profiles: pd.DataFrame,
    monthly_activity: pd.DataFrame,
) -> dict[str, list[dict]]:
    """Convert the validated sample-month artifact to Reviewer 360 JSON."""
    if profiles.empty or monthly_activity.empty:
        return {}

    sample_users = profiles[["sample_id", "user_id"]].copy()
    sample_users["sample_id"] = sample_users["sample_id"].astype(str)
    sample_users["user_id"] = sample_users["user_id"].astype(str)
    activity = monthly_activity.merge(
        sample_users,
        on="sample_id",
        how="left",
        validate="many_to_one",
    ).sort_values(["user_id", "year_month"], kind="mergesort")

    result: dict[str, list[dict]] = {}
    for user_id, group in activity.groupby("user_id", sort=True):
        result[str(user_id)] = [
            {
                "month": str(row.year_month),
                "reviewCount": int(row.review_count),
                "uniqueBusinessCount": int(row.unique_business_count),
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
    # 지연 import: 이 스크립트를 직접 실행할 때만 core.data(streamlit)가
    # 필요하다. 순수 export 함수(build_row/build_detail 등)만 재사용하는
    # 쪽(예: api/)은 이 줄을 절대 거치지 않는다.
    from core.data import load_app_data

    data = load_app_data()
    profiles = data.reviewer_profiles

    if profiles.empty:
        raise SystemExit("reviewer_profiles is empty. Check the v04 data files.")

    print(f"loaded {len(profiles):,} reviewer profiles (mode={data.data_mode})")

    ordered = profiles.sort_values("priority_rank")
    reviewer_region, monthly_activity_frame = load_derived_reviewer_data(profiles)

    # Worklist rows are bundled; per-reviewer detail is served from public/ and
    # fetched only when a Reviewer 360 screen opens, so the whole cohort stays
    # browsable without a multi-megabyte bundle.
    write(OUT_DIR / "operations.json", export_operations(data, profiles))
    write(OUT_DIR / "trust.json", export_trust(data))
    write(OUT_DIR / "playbooks.json", export_playbooks())
    write(OUT_DIR / "strategies.json", export_strategies())
    write(
        OUT_DIR / "regional.json",
        export_regional(profiles, reviewer_region),
    )
    write(OUT_DIR / "reviewers.json", [build_row(row) for _, row in ordered.iterrows()])

    monthly_activity = export_monthly_activity(
        profiles,
        monthly_activity_frame,
    )
    details = {}
    for _, row in ordered.iterrows():
        user_id = str(row["user_id"])
        detail = build_detail(row)
        detail["monthlyActivity"] = monthly_activity.get(user_id, [])
        details[user_id] = detail
    write(PUBLIC_DIR / "reviewer-details.json", details)

    print(f"exported {len(ordered):,} reviewers")



def export_regional(
    profiles: pd.DataFrame,
    reviewer_region: pd.DataFrame,
) -> dict:
    """Aggregate the pipeline-owned reviewer-region rows for React."""
    minimum_reviewers = 30
    if profiles.empty or reviewer_region.empty:
        return {"available": False, "regions": [], "minimumReviewers": minimum_reviewers}

    cohort = profiles.copy()
    cohort["sample_id"] = cohort["sample_id"].astype(str)
    cohort["user_id"] = cohort["user_id"].astype(str)

    selection_year = _i(cohort["selection_year"].iloc[0], 2018)
    comparison_year = _i(cohort["comparison_year"].iloc[0], 2017)

    per_sample = reviewer_region.merge(
        cohort[
            [
                "sample_id",
                "predicted_state",
                "crm_target",
            ]
        ],
        on="sample_id",
        how="inner",
        validate="one_to_one",
    )

    # Pick the city selected by the largest number of reviewers in each region.
    top_city = (
        per_sample.dropna(subset=["top_city"])
        .groupby(["state", "top_city"])
        .size()
        .reset_index(name="reviewers")
        .sort_values(
            ["state", "reviewers", "top_city"],
            ascending=[True, False, True],
            kind="mergesort",
        )
        .drop_duplicates("state")
        .set_index("state")["top_city"]
    )

    regions = []
    for state, group in per_sample.groupby("state"):
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
        "coveredReviewers": int(len(per_sample)),
        "totalReviewers": int(len(cohort)),
        "regions": regions,
    }

if __name__ == "__main__":
    main()
