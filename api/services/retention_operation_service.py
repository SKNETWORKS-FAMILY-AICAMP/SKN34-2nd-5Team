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
ALERT_STATUSES = {"open", "completed", "dismissed"}


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


def _create_review_alert_if_needed(
    connection: Connection,
    values: dict,
    operator: OperatorIdentity,
) -> None:
    due_at = values.get("snooze_until")
    if due_at is None:
        return
    existing = connection.execute(
        text(
            "SELECT alert_id FROM retention_review_alerts "
            "WHERE reviewer_user_id = :reviewer_user_id "
            "AND model_version = :model_version AND due_at = :due_at"
        ),
        {
            "reviewer_user_id": values["reviewer_user_id"],
            "model_version": values["model_version"],
            "due_at": due_at,
        },
    ).first()
    if existing is not None:
        return

    region = connection.execute(
        text(
            "SELECT state FROM reviewer_region "
            "WHERE model_version = :model_version AND sample_id = :sample_id LIMIT 1"
        ),
        values,
    ).scalar_one_or_none()
    scoped_operator = None
    if region:
        scoped_operator = connection.execute(
            text(
                "SELECT auth_subject, operator_label FROM retention_operator_scopes "
                "WHERE region_code = :region AND is_active = 1 "
                "ORDER BY created_at ASC LIMIT 1"
            ),
            {"region": region},
        ).mappings().first()
    assigned_subject = values.get("assignee_subject") or (
        scoped_operator["auth_subject"] if scoped_operator else None
    )
    assigned_name = None
    if assigned_subject == operator.subject:
        assigned_name = operator.name
    elif scoped_operator and assigned_subject == scoped_operator["auth_subject"]:
        assigned_name = scoped_operator["operator_label"]

    result = connection.execute(
        text(
            """
            INSERT INTO retention_review_alerts (
                reviewer_user_id, model_version, sample_id, due_at, status,
                assigned_subject, assigned_name,
                created_by_subject, created_by_name
            ) VALUES (
                :reviewer_user_id, :model_version, :sample_id, :due_at, 'open',
                :assigned_subject, :assigned_name,
                :actor_subject, :actor_name
            )
            """
        ),
        {
            **values,
            "due_at": due_at,
            "assigned_subject": assigned_subject,
            "assigned_name": assigned_name,
        },
    )
    alert_id = int(result.lastrowid)
    connection.execute(
        text(
            """
            INSERT INTO retention_review_alert_history (
                alert_id, action_type, from_status, to_status,
                note, actor_subject, actor_name
            ) VALUES (
                :alert_id, 'created', NULL, 'open',
                '재검토 시점 지정', :actor_subject, :actor_name
            )
            """
        ),
        {"alert_id": alert_id, **values},
    )


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
        _create_review_alert_if_needed(connection, values, operator)
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


def list_all_history(engine: Engine, limit: int = 200) -> list[dict]:
    """Return the append-only decision audit stream for the operations console."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT * FROM retention_decision_history "
                "ORDER BY changed_at DESC, history_id DESC LIMIT :limit"
            ),
            {"limit": limit},
        ).mappings().all()
    return [
        {
            "historyId": int(row["history_id"]),
            "reviewerUserId": row["reviewer_user_id"],
            "action": row["action_type"],
            "fromDecision": row["from_decision"],
            "toDecision": row["to_decision"],
            "actor": {"subject": row["actor_subject"], "name": row["actor_name"]},
            "changedAt": _iso(row["changed_at"]),
        }
        for row in rows
    ]


def list_all_interactions(engine: Engine, limit: int = 200) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT * FROM retention_interactions "
                "ORDER BY contacted_at DESC, interaction_id DESC LIMIT :limit"
            ),
            {"limit": limit},
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


def list_due_reviews(engine: Engine, limit: int = 200) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT * FROM retention_decisions "
                "WHERE snooze_until IS NOT NULL "
                "ORDER BY snooze_until ASC LIMIT :limit"
            ),
            {"limit": limit},
        ).mappings().all()
    return [_decision_json(row) for row in rows]


def list_operator_scopes(engine: Engine) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT auth_subject, operator_label, region_code, is_active "
                "FROM retention_operator_scopes ORDER BY region_code, operator_label"
            )
        ).mappings().all()
    return [
        {
            "subject": row["auth_subject"],
            "name": row["operator_label"],
            "region": row["region_code"],
            "active": bool(row["is_active"]),
        }
        for row in rows
    ]


def regions_for_identity(engine: Engine, identity: OperatorIdentity) -> list[str] | None:
    if identity.access_role in {"ADMIN", "VIEWER"}:
        return None
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT region_code FROM retention_operator_scopes "
                "WHERE auth_subject = :subject AND is_active = 1 ORDER BY region_code"
            ),
            {"subject": identity.subject},
        ).scalars().all()
    return list(rows)


def reviewer_ids_for_regions(engine: Engine, regions: list[str]) -> set[str]:
    if not regions:
        return set()
    from sqlalchemy import bindparam

    statement = text(
        "SELECT DISTINCT sample.user_id FROM reviewer_region AS region_row "
        "INNER JOIN cohort_samples AS sample "
        "ON sample.model_version = region_row.model_version "
        "AND sample.sample_id = region_row.sample_id "
        "WHERE region_row.state IN :regions"
    ).bindparams(bindparam("regions", expanding=True))
    with engine.connect() as connection:
        return set(connection.execute(statement, {"regions": regions}).scalars().all())


def _alert_json(row) -> dict:
    return {
        "alertId": int(row["alert_id"]),
        "reviewerUserId": row["reviewer_user_id"],
        "modelVersion": row["model_version"],
        "sampleId": row["sample_id"],
        "region": row.get("region_code"),
        "topCity": row.get("top_city"),
        "dueAt": _iso(row["due_at"]),
        "status": row["status"],
        "decision": row.get("manager_decision"),
        "note": row.get("decision_note"),
        "riskType": row.get("risk_type"),
        "modelJudgment": row.get("model_judgment"),
        "assignedTo": {
            "subject": row.get("assigned_subject"),
            "name": row.get("assigned_name"),
        },
        "resolutionNote": row.get("resolution_note"),
        "resolvedBy": {
            "subject": row.get("resolved_by_subject"),
            "name": row.get("resolved_by_name"),
        },
        "resolvedAt": _iso(row.get("resolved_at")),
        "createdAt": _iso(row["created_at"]),
        "updatedAt": _iso(row["updated_at"]),
    }


def list_review_alerts(
    engine: Engine,
    identity: OperatorIdentity,
    limit: int = 200,
) -> list[dict]:
    allowed_regions = regions_for_identity(engine, identity)
    if allowed_regions == []:
        return []
    sql = """
        SELECT alert_row.*, decision_row.manager_decision,
               decision_row.note AS decision_note, decision_row.risk_type,
               decision_row.model_judgment, region_row.state AS region_code,
               region_row.top_city
        FROM retention_review_alerts AS alert_row
        LEFT JOIN retention_decisions AS decision_row
          ON decision_row.reviewer_user_id = alert_row.reviewer_user_id
        LEFT JOIN reviewer_region AS region_row
          ON region_row.model_version = alert_row.model_version
         AND region_row.sample_id = alert_row.sample_id
    """
    params: dict = {"limit": limit}
    if allowed_regions is not None:
        sql += " WHERE region_row.state IN :regions"
        params["regions"] = tuple(allowed_regions)
    sql += " ORDER BY (alert_row.status = 'open') DESC, alert_row.due_at ASC LIMIT :limit"
    statement = text(sql)
    if allowed_regions is not None:
        from sqlalchemy import bindparam

        statement = statement.bindparams(bindparam("regions", expanding=True))
    with engine.connect() as connection:
        rows = connection.execute(statement, params).mappings().all()
    return [_alert_json(row) for row in rows]


def list_review_alert_history(
    engine: Engine,
    alert_id: int,
    identity: OperatorIdentity,
) -> list[dict]:
    allowed_regions = regions_for_identity(engine, identity)
    with engine.connect() as connection:
        alert_region = connection.execute(
            text(
                """
                SELECT region_row.state
                FROM retention_review_alerts AS alert_row
                LEFT JOIN reviewer_region AS region_row
                  ON region_row.model_version = alert_row.model_version
                 AND region_row.sample_id = alert_row.sample_id
                WHERE alert_row.alert_id = :alert_id
                """
            ),
            {"alert_id": alert_id},
        ).scalar_one_or_none()
        if alert_region is None:
            raise ValueError("해당 재검토 알림을 찾을 수 없습니다")
        if allowed_regions is not None and alert_region not in allowed_regions:
            raise PermissionError("배정된 권역의 알림만 조회할 수 있습니다")
        rows = connection.execute(
            text(
                "SELECT * FROM retention_review_alert_history "
                "WHERE alert_id = :alert_id ORDER BY changed_at DESC, history_id DESC"
            ),
            {"alert_id": alert_id},
        ).mappings().all()
    return [
        {
            "historyId": int(row["history_id"]),
            "alertId": int(row["alert_id"]),
            "action": row["action_type"],
            "fromStatus": row["from_status"],
            "toStatus": row["to_status"],
            "note": row["note"],
            "actor": {"subject": row["actor_subject"], "name": row["actor_name"]},
            "changedAt": _iso(row["changed_at"]),
        }
        for row in rows
    ]


def resolve_review_alert(
    engine: Engine,
    alert_id: int,
    status: str,
    note: str | None,
    operator: OperatorIdentity,
) -> dict:
    if status not in {"completed", "dismissed"}:
        raise ValueError("알림은 처리 완료 또는 제외 상태로만 변경할 수 있습니다")
    allowed_regions = regions_for_identity(engine, operator)
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT alert_row.*, region_row.state AS region_code, region_row.top_city,
                       decision_row.manager_decision, decision_row.note AS decision_note,
                       decision_row.risk_type, decision_row.model_judgment
                FROM retention_review_alerts AS alert_row
                LEFT JOIN reviewer_region AS region_row
                  ON region_row.model_version = alert_row.model_version
                 AND region_row.sample_id = alert_row.sample_id
                LEFT JOIN retention_decisions AS decision_row
                  ON decision_row.reviewer_user_id = alert_row.reviewer_user_id
                WHERE alert_row.alert_id = :alert_id FOR UPDATE
                """
            ),
            {"alert_id": alert_id},
        ).mappings().first()
        if row is None:
            raise ValueError("재검토 알림을 찾을 수 없습니다")
        if allowed_regions is not None and row["region_code"] not in allowed_regions:
            raise PermissionError("배정된 권역의 알림만 처리할 수 있습니다")
        if row["status"] != "open":
            raise RuntimeError("이미 처리된 재검토 알림입니다")
        now = datetime.utcnow()
        connection.execute(
            text(
                """
                UPDATE retention_review_alerts SET
                    status = :status, resolution_note = :note,
                    resolved_by_subject = :actor_subject,
                    resolved_by_name = :actor_name, resolved_at = :resolved_at
                WHERE alert_id = :alert_id
                """
            ),
            {
                "alert_id": alert_id,
                "status": status,
                "note": note,
                "actor_subject": operator.subject,
                "actor_name": operator.name,
                "resolved_at": now,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO retention_review_alert_history (
                    alert_id, action_type, from_status, to_status,
                    note, actor_subject, actor_name, changed_at
                ) VALUES (
                    :alert_id, :action, 'open', :status,
                    :note, :actor_subject, :actor_name, :changed_at
                )
                """
            ),
            {
                "alert_id": alert_id,
                "action": status,
                "status": status,
                "note": note,
                "actor_subject": operator.subject,
                "actor_name": operator.name,
                "changed_at": now,
            },
        )
        updated = dict(row)
        updated.update(
            status=status,
            resolution_note=note,
            resolved_by_subject=operator.subject,
            resolved_by_name=operator.name,
            resolved_at=now,
            updated_at=now,
        )
    return _alert_json(updated)
