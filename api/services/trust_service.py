"""Trust Center(trust.json) 조회.

v04(3클래스 메인) + v03(3클래스 비교, 접힘) + v02(이진분류 비교, 접힘).
export_trust()/_multiclass_trust_block()/_v03_top20()/_v02_block()
(scripts/export_frontend_data.py:433-580)과 대응한다.

DB의 feature_group_label은 cp949 mojibake는 없지만(정상 한글), 모델 세대별로
텍스트 자체가 다르다(v02 "리뷰 작성 간격" vs v03/v04 "작성 간격"). 안정적인
feature_group(ascii 키) 기준으로 FEATURE_GROUP_LABELS에서 정규화한다 —
export 스크립트가 하던 것과 목적은 같지만 원인은 다르다.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

STATE_ORDER = ["retained", "weakened", "stopped"]
FEATURE_IMPORTANCE_LIMIT = 15

# DB의 feature_group_label 텍스트가 모델 세대마다 다르다 — v02는
# "리뷰 작성 간격", v03/v04는 "작성 간격"으로 저장되어 있다(원본 CSV 세대
# 차이, cp949 mojibake 아님). feature_group(ascii 키)은 세 버전 모두 동일
# 하므로 여기서 정규화한다. scripts/export_frontend_data.py의
# FEATURE_GROUP_LABELS 하드코딩과 같은 목적, 같은 값이다.
FEATURE_GROUP_LABELS = {
    "interval": "작성 간격",
    "activity": "리뷰 활동량",
    "business": "음식점 탐색",
}


def _group_label(feature_group: str, feature_group_label: str) -> str:
    return FEATURE_GROUP_LABELS.get(feature_group, feature_group_label)


def _multiclass_block(conn, model_version: str) -> dict:
    row = conn.execute(
        text(
            "SELECT validation_samples, macro_f1, macro_pr_auc, "
            "macro_ovr_roc_auc, balanced_accuracy, accuracy, "
            "retained_precision, retained_recall, retained_f1, "
            "retained_support, retained_pr_auc, "
            "weakened_precision, weakened_recall, weakened_f1, "
            "weakened_support, weakened_pr_auc, "
            "stopped_precision, stopped_recall, stopped_f1, "
            "stopped_support, stopped_pr_auc "
            "FROM model_validation_metrics "
            "WHERE model_version = :v AND record_type = 'final_test'"
        ),
        {"v": model_version},
    ).mappings().first()

    if row is None:
        return {"available": False}

    confusion_rows = conn.execute(
        text(
            "SELECT actual_state, predicted_state, users "
            "FROM model_confusion_matrix "
            "WHERE model_version = :v AND split = 'final_test'"
        ),
        {"v": model_version},
    ).mappings().all()
    order_index = {state: i for i, state in enumerate(STATE_ORDER)}
    confusion_rows = sorted(
        confusion_rows,
        key=lambda r: (
            order_index.get(r["actual_state"], 99),
            order_index.get(r["predicted_state"], 99),
        ),
    )

    top_k_rows = conn.execute(
        text(
            "SELECT target_rate, target_users, status_loss_captured, "
            "status_loss_precision, status_loss_recall, status_loss_lift "
            "FROM model_topk_metrics "
            "WHERE model_version = :v AND split = 'final_test' "
            "AND ranking = 'unified' ORDER BY target_rate"
        ),
        {"v": model_version},
    ).mappings().all()

    feature_rows = conn.execute(
        text(
            "SELECT rank_no, feature, feature_group, feature_group_label, importance_mean, "
            "importance_share_pct, baseline_pr_auc "
            "FROM feature_importance "
            "WHERE model_version = :v AND split = 'final_test' "
            "ORDER BY rank_no LIMIT :limit"
        ),
        {"v": model_version, "limit": FEATURE_IMPORTANCE_LIMIT},
    ).mappings().all()

    group_rows = conn.execute(
        text(
            "SELECT feature_group, feature_group_label, feature_count, rank_no, importance_mean "
            "FROM feature_group_importance "
            "WHERE model_version = :v AND split = 'final_test' ORDER BY rank_no"
        ),
        {"v": model_version},
    ).mappings().all()

    def class_perf(prefix: str, label: str) -> dict:
        return {
            "className": label,
            "precision": float(row[f"{prefix}_precision"]),
            "recall": float(row[f"{prefix}_recall"]),
            "f1": float(row[f"{prefix}_f1"]),
            "prAuc": float(row[f"{prefix}_pr_auc"]),
            "support": int(row[f"{prefix}_support"]),
        }

    return {
        "available": True,
        "validationSamples": int(row["validation_samples"]),
        "overall": {
            "macroF1": float(row["macro_f1"]),
            "macroPrAuc": float(row["macro_pr_auc"]),
            "macroRocAuc": float(row["macro_ovr_roc_auc"]),
            "balancedAccuracy": float(row["balanced_accuracy"]),
            "accuracy": float(row["accuracy"]),
        },
        "classPerformance": [
            class_perf("retained", "파워 지위 유지"),
            class_perf("weakened", "파워 지위 약화"),
            class_perf("stopped", "리뷰 활동 중단"),
        ],
        "confusionMatrix": [
            {
                "actual": r["actual_state"],
                "predicted": r["predicted_state"],
                "users": int(r["users"]),
            }
            for r in confusion_rows
        ],
        "topK": [
            {
                "targetRate": float(r["target_rate"]),
                "targetUsers": int(r["target_users"]),
                "captured": int(r["status_loss_captured"]),
                "precision": float(r["status_loss_precision"]),
                "recall": float(r["status_loss_recall"]),
                "lift": float(r["status_loss_lift"]),
            }
            for r in top_k_rows
        ],
        "featureImportance": [
            {
                "rank": int(r["rank_no"]),
                "feature": r["feature"],
                "group": _group_label(r["feature_group"], r["feature_group_label"]),
                "importance": float(r["importance_mean"]),
                "sharePercent": float(r["importance_share_pct"]),
            }
            for r in feature_rows
        ],
        "groupImportance": [
            {
                "group": _group_label(r["feature_group"], r["feature_group_label"]),
                "featureCount": int(r["feature_count"]),
                "importance": float(r["importance_mean"]),
                "rank": int(r["rank_no"]),
            }
            for r in group_rows
        ],
        "_baseline_pr_auc": float(feature_rows[0]["baseline_pr_auc"])
        if feature_rows
        else 0.0,
    }


def _v03_top20(conn) -> dict | None:
    row = conn.execute(
        text(
            "SELECT target_users, status_loss_captured, status_loss_precision, "
            "status_loss_recall, status_loss_lift FROM model_topk_metrics "
            "WHERE model_version = 'v03' AND split = 'final_test' "
            "AND ranking = 'unified' AND target_rate = 0.20"
        )
    ).mappings().first()
    if row is None:
        return None
    return {
        "targetUsers": int(row["target_users"]),
        "captured": int(row["status_loss_captured"]),
        "precision": float(row["status_loss_precision"]),
        "recall": float(row["status_loss_recall"]),
        "lift": float(row["status_loss_lift"]),
    }


def _v02_block(conn) -> dict:
    rows = conn.execute(
        text(
            "SELECT split, selection_year, precision_score, recall_score, f1, "
            "roc_auc, pr_auc FROM model_binary_validation_metrics "
            "ORDER BY selection_year"
        )
    ).mappings().all()

    dataset_labels = {"validation": "Validation", "final_test": "Test"}
    dataset_comparison = [
        {
            "dataset": dataset_labels.get(r["split"], r["split"]),
            "precision": float(r["precision_score"]),
            "recall": float(r["recall_score"]),
            "f1": float(r["f1"]),
            "rocAuc": float(r["roc_auc"]),
            "prAuc": float(r["pr_auc"]),
        }
        for r in rows
    ]
    test_row = next((r for r in rows if r["split"] == "final_test"), None)

    top_k_rows = conn.execute(
        text(
            "SELECT target_rate, target_users, captured_churn_users, "
            "precision_at_k, recall_at_k, lift_at_k "
            "FROM model_binary_topk_metrics "
            "WHERE model_version = 'v02' AND split = 'final_test' "
            "ORDER BY target_rate"
        )
    ).mappings().all()

    feature_rows = conn.execute(
        text(
            "SELECT rank_no, feature, feature_group, feature_group_label, importance_mean, "
            "importance_share_pct FROM feature_importance "
            "WHERE model_version = 'v02' AND split = 'final_test' "
            "ORDER BY rank_no LIMIT :limit"
        ),
        {"limit": FEATURE_IMPORTANCE_LIMIT},
    ).mappings().all()

    group_rows = conn.execute(
        text(
            "SELECT feature_group, feature_group_label, feature_count, rank_no, importance_mean "
            "FROM feature_group_importance "
            "WHERE model_version = 'v02' AND split = 'final_test' ORDER BY rank_no"
        )
    ).mappings().all()

    return {
        "available": bool(rows) or bool(top_k_rows),
        "overall": {
            "precision": float(test_row["precision_score"]) if test_row else 0.0,
            "recall": float(test_row["recall_score"]) if test_row else 0.0,
            "rocAuc": float(test_row["roc_auc"]) if test_row else 0.0,
            "prAuc": float(test_row["pr_auc"]) if test_row else 0.0,
        },
        "datasetComparison": dataset_comparison,
        "topK": [
            {
                "targetRatePercent": float(r["target_rate"]) * 100,
                "targetUsers": int(r["target_users"]),
                "capturedChurnUsers": int(r["captured_churn_users"]),
                "precision": float(r["precision_at_k"]),
                "recall": float(r["recall_at_k"]),
                "lift": float(r["lift_at_k"]),
            }
            for r in top_k_rows
        ],
        "featureImportance": [
            {
                "rank": int(r["rank_no"]),
                "feature": r["feature"],
                "group": _group_label(r["feature_group"], r["feature_group_label"]),
                "importance": float(r["importance_mean"]),
                "sharePercent": float(r["importance_share_pct"]),
            }
            for r in feature_rows
        ],
        "groupImportance": [
            {
                "group": _group_label(r["feature_group"], r["feature_group_label"]),
                "featureCount": int(r["feature_count"]),
                "importance": float(r["importance_mean"]),
                "rank": int(r["rank_no"]),
            }
            for r in group_rows
        ],
    }


def get_trust_data(engine: Engine) -> dict:
    with engine.connect() as conn:
        version_row = conn.execute(
            text(
                "SELECT test_target_year FROM model_versions "
                "WHERE model_version = 'v04'"
            )
        ).one()

        v04 = _multiclass_block(conn, "v04")
        v03 = _multiclass_block(conn, "v03")
        v03["top20"] = _v03_top20(conn)
        v02 = _v02_block(conn)

    baseline_pr_auc = v04.pop("_baseline_pr_auc", 0.0)
    v03.pop("_baseline_pr_auc", None)

    return {
        "modelVersion": "v04",
        "validationPeriod": f"Test {version_row.test_target_year}",
        "overall": v04["overall"],
        "classPerformance": v04["classPerformance"],
        "confusionMatrix": v04["confusionMatrix"],
        "topK": v04["topK"],
        "featureImportance": v04["featureImportance"],
        "groupImportance": v04["groupImportance"],
        "baselinePrAuc": baseline_pr_auc,
        "v03": v03,
        "v02": v02,
    }
