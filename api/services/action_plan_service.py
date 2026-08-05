"""Persistence for individual interventions and regional campaign plans."""
from __future__ import annotations

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection, Engine

from api.auth_context import OperatorIdentity


PLAN_TYPES = {"individual", "regional"}
PLAN_STATUSES = {"draft", "saved", "archived"}
CHANNELS = {"app", "email", "push", "phone", "operator"}


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _children(connection: Connection, plan_ids: list[int]) -> tuple[dict, dict, dict]:
    channels = {plan_id: [] for plan_id in plan_ids}
    businesses = {plan_id: [] for plan_id in plan_ids}
    milestones = {plan_id: [] for plan_id in plan_ids}
    if not plan_ids:
        return channels, businesses, milestones
    clause = bindparam("plan_ids", expanding=True)
    for row in connection.execute(
        text("SELECT plan_id, channel FROM retention_action_plan_channels WHERE plan_id IN :plan_ids ORDER BY channel").bindparams(clause),
        {"plan_ids": plan_ids},
    ).mappings():
        channels[int(row["plan_id"])].append(row["channel"])
    for row in connection.execute(
        text("SELECT plan_id, business_id FROM retention_action_plan_businesses WHERE plan_id IN :plan_ids ORDER BY display_order, business_id").bindparams(clause),
        {"plan_ids": plan_ids},
    ).mappings():
        businesses[int(row["plan_id"])].append(row["business_id"])
    for row in connection.execute(
        text("SELECT plan_id, day_offset, metric_code, metric_label, observation_note FROM retention_action_plan_milestones WHERE plan_id IN :plan_ids ORDER BY day_offset, metric_code").bindparams(clause),
        {"plan_ids": plan_ids},
    ).mappings():
        milestones[int(row["plan_id"])].append({
            "dayOffset": int(row["day_offset"]),
            "metricCode": row["metric_code"],
            "metricLabel": row["metric_label"],
            "observationNote": row["observation_note"],
        })
    return channels, businesses, milestones


def _plan_json(row, channels: list[str], businesses: list[str], milestones: list[dict]) -> dict:
    return {
        "planId": int(row["plan_id"]),
        "planType": row["plan_type"],
        "modelVersion": row["model_version"],
        "reviewerUserId": row["reviewer_user_id"],
        "sampleId": row["sample_id"],
        "regionCode": row["region_code"],
        "targetScope": row["target_scope"],
        "cityKey": row["city_key"],
        "cityName": row["city_name"],
        "targetListId": int(row["target_list_id"]) if row["target_list_id"] is not None else None,
        "managerDecision": row["manager_decision"],
        "actionType": row["action_type"],
        "messageTitle": row["message_title"],
        "messageBody": row["message_body"],
        "status": row["plan_status"],
        "channels": channels,
        "businessIds": businesses,
        "milestones": milestones,
        "createdBy": {"subject": row["created_by_subject"], "name": row["created_by_name"]},
        "updatedBy": {"subject": row["updated_by_subject"], "name": row["updated_by_name"]},
        "lockVersion": int(row["lock_version"]),
        "createdAt": _iso(row["created_at"]),
        "updatedAt": _iso(row["updated_at"]),
    }


def _validate(payload: dict) -> None:
    if payload["plan_type"] not in PLAN_TYPES:
        raise ValueError("지원하지 않는 실행안 유형입니다.")
    if payload["status"] not in PLAN_STATUSES:
        raise ValueError("지원하지 않는 실행안 상태입니다.")
    if any(channel not in CHANNELS for channel in payload["channels"]):
        raise ValueError("지원하지 않는 전달 채널입니다.")
    if payload["plan_type"] == "individual" and not (payload.get("reviewer_user_id") and payload.get("sample_id")):
        raise ValueError("개인 실행안에는 리뷰어와 표본 정보가 필요합니다.")
    if payload["plan_type"] == "regional" and not payload.get("region_code"):
        raise ValueError("지역 실행안에는 권역 코드가 필요합니다.")
    if payload["plan_type"] == "individual" and any(
        payload.get(key) for key in ("target_scope", "city_key", "city_name")
    ):
        raise ValueError("개인 실행안에는 지역 범위를 저장할 수 없습니다.")
    if payload["plan_type"] == "regional":
        if payload.get("target_scope") not in {"region", "city"}:
            raise ValueError("지역 실행안에는 대상 범위가 필요합니다.")
        if payload["target_scope"] == "city" and not (
            payload.get("city_key") and payload.get("city_name")
        ):
            raise ValueError("도시 실행안에는 도시 정보가 필요합니다.")
        if payload["target_scope"] == "region" and any(
            payload.get(key) for key in ("city_key", "city_name")
        ):
            raise ValueError("권역 전체 실행안에는 도시 정보를 저장할 수 없습니다.")
    if any(item["day_offset"] not in {30, 60, 90} for item in payload["milestones"]):
        raise ValueError("측정 시점은 30일, 60일, 90일만 지원합니다.")


def _replace_children(connection: Connection, plan_id: int, payload: dict) -> None:
    connection.execute(text("DELETE FROM retention_action_plan_channels WHERE plan_id = :plan_id"), {"plan_id": plan_id})
    connection.execute(text("DELETE FROM retention_action_plan_businesses WHERE plan_id = :plan_id"), {"plan_id": plan_id})
    connection.execute(text("DELETE FROM retention_action_plan_milestones WHERE plan_id = :plan_id"), {"plan_id": plan_id})
    for channel in dict.fromkeys(payload["channels"]):
        connection.execute(text("INSERT INTO retention_action_plan_channels (plan_id, channel) VALUES (:plan_id, :channel)"), {"plan_id": plan_id, "channel": channel})
    for order, business_id in enumerate(dict.fromkeys(payload["business_ids"])):
        connection.execute(text("INSERT INTO retention_action_plan_businesses (plan_id, business_id, display_order) VALUES (:plan_id, :business_id, :display_order)"), {"plan_id": plan_id, "business_id": business_id, "display_order": order})
    for item in payload["milestones"]:
        connection.execute(text("""
            INSERT INTO retention_action_plan_milestones
                (plan_id, day_offset, metric_code, metric_label, observation_note)
            VALUES (:plan_id, :day_offset, :metric_code, :metric_label, :observation_note)
        """), {"plan_id": plan_id, **item})


def list_action_plans(engine: Engine, plan_type: str | None = None) -> list[dict]:
    query = "SELECT * FROM retention_action_plans"
    params = {}
    if plan_type:
        query += " WHERE plan_type = :plan_type"
        params["plan_type"] = plan_type
    query += " ORDER BY updated_at DESC, plan_id DESC"
    with engine.connect() as connection:
        rows = connection.execute(text(query), params).mappings().all()
        ids = [int(row["plan_id"]) for row in rows]
        channels, businesses, milestones = _children(connection, ids)
    return [_plan_json(row, channels[int(row["plan_id"])], businesses[int(row["plan_id"])], milestones[int(row["plan_id"])]) for row in rows]


def save_action_plan(engine: Engine, payload: dict, operator: OperatorIdentity, plan_id: int | None = None) -> dict:
    _validate(payload)
    with engine.begin() as connection:
        previous = None
        if plan_id is not None:
            previous = connection.execute(text("SELECT * FROM retention_action_plans WHERE plan_id = :plan_id FOR UPDATE"), {"plan_id": plan_id}).mappings().first()
            if previous is None:
                raise ValueError("실행안을 찾을 수 없습니다.")
            expected = payload.get("expected_lock_version")
            if expected is not None and int(expected) != int(previous["lock_version"]):
                raise RuntimeError("다른 운영자가 먼저 수정했습니다. 새로고침 후 다시 시도하세요.")
        values = {
            **payload,
            "actor_subject": operator.subject,
            "actor_name": operator.name,
        }
        if previous is None:
            result = connection.execute(text("""
                INSERT INTO retention_action_plans (
                    plan_type, model_version, reviewer_user_id, sample_id, region_code,
                    target_scope, city_key, city_name,
                    target_list_id, manager_decision, action_type, message_title,
                    message_body, plan_status, created_by_subject, created_by_name,
                    updated_by_subject, updated_by_name
                ) VALUES (
                    :plan_type, :model_version, :reviewer_user_id, :sample_id, :region_code,
                    :target_scope, :city_key, :city_name,
                    :target_list_id, :manager_decision, :action_type, :message_title,
                    :message_body, :status, :actor_subject, :actor_name,
                    :actor_subject, :actor_name
                )
            """), values)
            plan_id = int(result.lastrowid)
        else:
            connection.execute(text("""
                UPDATE retention_action_plans SET
                    region_code = :region_code, target_scope = :target_scope,
                    city_key = :city_key, city_name = :city_name,
                    target_list_id = :target_list_id, manager_decision = :manager_decision,
                    action_type = :action_type, message_title = :message_title,
                    message_body = :message_body, plan_status = :status,
                    updated_by_subject = :actor_subject, updated_by_name = :actor_name,
                    lock_version = lock_version + 1
                WHERE plan_id = :plan_id
            """), {**values, "plan_id": plan_id})
        _replace_children(connection, int(plan_id), payload)
        row = connection.execute(text("SELECT * FROM retention_action_plans WHERE plan_id = :plan_id"), {"plan_id": plan_id}).mappings().one()
        channels, businesses, milestones = _children(connection, [int(plan_id)])
    return _plan_json(row, channels[int(plan_id)], businesses[int(plan_id)], milestones[int(plan_id)])
