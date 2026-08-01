"""Transactional persistence for reviewer-retention operations."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from api.auth_context import OperatorIdentity


DECISIONS = {
    "리뷰 다시 시작 유도",
    "리뷰 활동 늘리기",
    "변화 지켜보기",
    "이번엔 제외",
}
CHANNELS = {"app", "email", "push", "phone", "other"}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _mysql_datetime(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _decision_json(row) -> dict:
    return {
        "reviewerUserId": row["reviewer_user_id"],
        "modelVersion": row["model_version"],
        "sampleId": row["sample_id"],
        "decision": row["manager_decision"],
        "note": row["note"],
        "assigneeSubject": row["assignee_subject"],
        "snoozeUntil": _iso(row["snooze_until"]),
        "riskType": row["risk_type"],
        "modelJudgment": row["model_judgment"],
        "updatedBy": {
            "subject": row["updated_by_subject"],
            "name": row["updated_by_name"],
        },
        "lockVersion": int(row["lock_version"]),
        "createdAt": _iso(row["created_at"]),
        "updatedAt": _iso(row["updated_at"]),
    }


def _require_sample(
    connection: Connection,
    reviewer_user_id: str,
    model_version: str,
    sample_id: str,
) -> None:
    exists = connection.execute(
        text(
            "SELECT 1 FROM cohort_samples "
            "WHERE user_id = :user_id AND model_version = :model_version "
            "AND sample_id = :sample_id LIMIT 1"
        ),
        {
            "user_id": reviewer_user_id,
            "model_version": model_version,
            "sample_id": sample_id,
        },
    ).first()
    if exists is None:
        raise ValueError("리뷰어와 모델 표본이 일치하지 않습니다")


def list_decisions(engine: Engine, model_version: str) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT * FROM retention_decisions "
                "WHERE model_version = :model_version ORDER BY updated_at DESC"
            ),
            {"model_version": model_version},
        ).mappings().all()
    return [_decision_json(row) for row in rows]


def save_decision(
    engine: Engine,
    reviewer_user_id: str,
    payload: dict,
    operator: OperatorIdentity,
) -> dict:
    if payload["decision"] not in DECISIONS:
        raise ValueError("지원하지 않는 관리자 판단입니다")

    with engine.begin() as connection:
        _require_sample(
            connection,
            reviewer_user_id,
            payload["model_version"],
            payload["sample_id"],
        )
        previous = connection.execute(
            text(
                "SELECT * FROM retention_decisions "
                "WHERE reviewer_user_id = :reviewer_user_id FOR UPDATE"
            ),
            {"reviewer_user_id": reviewer_user_id},
        ).mappings().first()

        values = {
            "reviewer_user_id": reviewer_user_id,
            "model_version": payload["model_version"],
            "sample_id": payload["sample_id"],
            "decision": payload["decision"],
            "note": payload.get("note"),
            "assignee_subject": payload.get("assignee_subject"),
            "snooze_until": _mysql_datetime(payload.get("snooze_until")),
            "risk_type": payload.get("risk_type"),
            "model_judgment": payload.get("model_judgment"),
            "actor_subject": operator.subject,
            "actor_name": operator.name,
        }
        if previous is None:
            connection.execute(
                text(
                    """
                    INSERT INTO retention_decisions (
                        reviewer_user_id, model_version, sample_id,
                        manager_decision, note, assignee_subject, snooze_until,
                        risk_type, model_judgment, updated_by_subject, updated_by_name
                    ) VALUES (
                        :reviewer_user_id, :model_version, :sample_id,
                        :decision, :note, :assignee_subject, :snooze_until,
                        :risk_type, :model_judgment, :actor_subject, :actor_name
                    )
                    """
                ),
                values,
            )
            action = "created"
        else:
            expected = payload.get("expected_lock_version")
            if expected is not None and int(expected) != int(previous["lock_version"]):
                raise RuntimeError("다른 운영자가 먼저 수정했습니다. 새로고침 후 다시 시도하세요")
            connection.execute(
                text(
                    """
                    UPDATE retention_decisions SET
                        model_version = :model_version,
                        sample_id = :sample_id,
                        manager_decision = :decision,
                        note = :note,
                        assignee_subject = :assignee_subject,
                        snooze_until = :snooze_until,
                        risk_type = :risk_type,
                        model_judgment = :model_judgment,
                        updated_by_subject = :actor_subject,
                        updated_by_name = :actor_name,
                        lock_version = lock_version + 1
                    WHERE reviewer_user_id = :reviewer_user_id
                    """
                ),
                values,
            )
            action = "updated"

        connection.execute(
            text(
                """
                INSERT INTO retention_decision_history (
                    reviewer_user_id, action_type, model_version, sample_id,
                    from_decision, to_decision, from_note, to_note,
                    from_assignee_subject, to_assignee_subject,
                    from_snooze_until, to_snooze_until,
                    actor_subject, actor_name
                ) VALUES (
                    :reviewer_user_id, :action, :model_version, :sample_id,
                    :from_decision, :decision, :from_note, :note,
                    :from_assignee, :assignee_subject,
                    :from_snooze, :snooze_until,
                    :actor_subject, :actor_name
                )
                """
            ),
            {
                **values,
                "action": action,
                "from_decision": previous["manager_decision"] if previous else None,
                "from_note": previous["note"] if previous else None,
                "from_assignee": previous["assignee_subject"] if previous else None,
                "from_snooze": previous["snooze_until"] if previous else None,
            },
        )
        row = connection.execute(
            text(
                "SELECT * FROM retention_decisions "
                "WHERE reviewer_user_id = :reviewer_user_id"
            ),
            {"reviewer_user_id": reviewer_user_id},
        ).mappings().one()
    return _decision_json(row)


def delete_decision(
    engine: Engine,
    reviewer_user_id: str,
    operator: OperatorIdentity,
) -> bool:
    with engine.begin() as connection:
        previous = connection.execute(
            text(
                "SELECT * FROM retention_decisions "
                "WHERE reviewer_user_id = :reviewer_user_id FOR UPDATE"
            ),
            {"reviewer_user_id": reviewer_user_id},
        ).mappings().first()
        if previous is None:
            return False
        connection.execute(
            text(
                """
                INSERT INTO retention_decision_history (
                    reviewer_user_id, action_type, model_version, sample_id,
                    from_decision, to_decision, from_note, to_note,
                    from_assignee_subject, to_assignee_subject,
                    from_snooze_until, to_snooze_until,
                    actor_subject, actor_name
                ) VALUES (
                    :reviewer_user_id, 'deleted', :model_version, :sample_id,
                    :from_decision, NULL, :from_note, NULL,
                    :from_assignee, NULL, :from_snooze, NULL,
                    :actor_subject, :actor_name
                )
                """
            ),
            {
                "reviewer_user_id": reviewer_user_id,
                "model_version": previous["model_version"],
                "sample_id": previous["sample_id"],
                "from_decision": previous["manager_decision"],
                "from_note": previous["note"],
                "from_assignee": previous["assignee_subject"],
                "from_snooze": previous["snooze_until"],
                "actor_subject": operator.subject,
                "actor_name": operator.name,
            },
        )
        connection.execute(
            text("DELETE FROM retention_decisions WHERE reviewer_user_id = :reviewer_user_id"),
            {"reviewer_user_id": reviewer_user_id},
        )
    return True


def list_history(engine: Engine, reviewer_user_id: str) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT * FROM retention_decision_history "
                "WHERE reviewer_user_id = :reviewer_user_id "
                "ORDER BY changed_at DESC, history_id DESC"
            ),
            {"reviewer_user_id": reviewer_user_id},
        ).mappings().all()
    return [
        {
            "historyId": int(row["history_id"]),
            "action": row["action_type"],
            "fromDecision": row["from_decision"],
            "toDecision": row["to_decision"],
            "actor": {"subject": row["actor_subject"], "name": row["actor_name"]},
            "changedAt": _iso(row["changed_at"]),
        }
        for row in rows
    ]


def add_interaction(
    engine: Engine,
    reviewer_user_id: str,
    payload: dict,
    operator: OperatorIdentity,
) -> dict:
    if payload["channel"] not in CHANNELS:
        raise ValueError("지원하지 않는 접촉 채널입니다")
    with engine.begin() as connection:
        _require_sample(
            connection,
            reviewer_user_id,
            payload["model_version"],
            payload["sample_id"],
        )
        values = {
            **payload,
            "reviewer_user_id": reviewer_user_id,
            "contacted_at": _mysql_datetime(payload["contacted_at"]),
            "actor_subject": operator.subject,
            "actor_name": operator.name,
        }
        result = connection.execute(
            text(
                """
                INSERT INTO retention_interactions (
                    reviewer_user_id, model_version, sample_id, channel,
                    contacted_at, note, actor_subject, actor_name
                ) VALUES (
                    :reviewer_user_id, :model_version, :sample_id, :channel,
                    :contacted_at, :note, :actor_subject, :actor_name
                )
                """
            ),
            values,
        )
        interaction_id = int(result.lastrowid)
    return {
        "interactionId": interaction_id,
        "reviewerUserId": reviewer_user_id,
        "channel": payload["channel"],
        "contactedAt": _iso(values["contacted_at"]),
        "note": payload.get("note"),
        "actor": {"subject": operator.subject, "name": operator.name},
    }


def list_interactions(engine: Engine, reviewer_user_id: str) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT * FROM retention_interactions "
                "WHERE reviewer_user_id = :reviewer_user_id "
                "ORDER BY contacted_at DESC, interaction_id DESC"
            ),
            {"reviewer_user_id": reviewer_user_id},
        ).mappings().all()
    return [
        {
            "interactionId": int(row["interaction_id"]),
            "reviewerUserId": row["reviewer_user_id"],
            "channel": row["channel"],
            "contactedAt": _iso(row["contacted_at"]),
            "note": row["note"],
            "actor": {"subject": row["actor_subject"], "name": row["actor_name"]},
            "createdAt": _iso(row["created_at"]),
        }
        for row in rows
    ]
