"""운영 홈(operations.json) 조회.

export_operations()/_derive_policy() (core/data.py:387)와 대응한다.
recallCeiling = target_users / (captured/recall) = target_users / total_status_loss
로 정리했다(recall = captured/total_status_loss이므로).

vw_model_top20_summary의 high_risk_rate와 달리, 여기서 쓰는 카운트 컬럼들은
정수 그대로라 규모 손 손실이 없다. 정밀도(precision/recall/lift)만
Python에서 float로 나눈다 — regional 화면에서 발견한 정수나눗셈 절삭을
피하기 위해서다.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

MODEL_VERSION = "v05_05_dl"


def get_operations_summary(engine: Engine) -> dict:
    with engine.connect() as conn:
        version_row = conn.execute(
            text(
                "SELECT test_target_year FROM model_versions "
                "WHERE model_version = :v"
            ),
            {"v": MODEL_VERSION},
        ).one()

        summary = conn.execute(
            text(
                """
                SELECT total_users, target_users, total_status_loss,
                       status_loss_captured, stopped_captured, weakened_captured
                FROM vw_model_top20_summary
                WHERE model_version = :v
                """
            ),
            {"v": MODEL_VERSION},
        ).one()

        state_counts = dict(
            conn.execute(
                text(
                    "SELECT predicted_state, COUNT(*) FROM model_predictions "
                    "WHERE model_version = :v GROUP BY predicted_state"
                ),
                {"v": MODEL_VERSION},
            ).all()
        )

    total_users = int(summary.total_users)
    target_users = int(summary.target_users)
    total_status_loss = int(summary.total_status_loss)
    captured = int(summary.status_loss_captured)

    precision = captured / target_users if target_users else 0.0
    recall = captured / total_status_loss if total_status_loss else 0.0
    base_rate = total_status_loss / total_users if total_users else 0.0
    lift = precision / base_rate if base_rate else None

    return {
        "modelVersion": MODEL_VERSION,
        "dataMode": "project",
        "snapshot": f"Test {version_row.test_target_year}",
        "targetYear": int(version_row.test_target_year),
        "totalReviewers": total_users,
        "targetUsers": target_users,
        "capturedUsers": captured,
        "precision": precision,
        "recall": recall,
        "lift": lift,
        "recallCeiling": (
            target_users / total_status_loss if total_status_loss else 0.0
        ),
        "retainedUsers": int(state_counts.get(0, 0)),
        "weakenedUsers": int(state_counts.get(1, 0)),
        "stoppedUsers": int(state_counts.get(2, 0)),
    }
