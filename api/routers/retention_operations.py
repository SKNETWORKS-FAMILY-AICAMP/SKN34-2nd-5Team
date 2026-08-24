from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from api.auth_context import OperatorIdentity, get_current_identity, get_current_operator
from api.db import get_engine
from api.services.retention_operation_service import (
    add_interaction,
    delete_decision,
    list_all_history,
    list_all_interactions,
    list_decisions,
    list_due_reviews,
    list_history,
    list_interactions,
    list_operator_scopes,
    list_review_alert_history,
    list_review_alerts,
    regions_for_identity,
    reviewer_ids_for_regions,
    resolve_review_alert,
    save_decision,
)
from api.services.action_plan_service import list_action_plans, save_action_plan
from api.services.target_list_service import (
    create_target_list,
    delete_target_list,
    list_target_lists,
)


router = APIRouter(
    prefix="/api/retention",
    tags=["retention-operations"],
    dependencies=[Depends(get_current_identity)],
)


class DecisionWrite(BaseModel):
    model_version: str = Field(alias="modelVersion", min_length=1, max_length=16)
    sample_id: str = Field(alias="sampleId", min_length=1, max_length=64)
    decision: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=5000)
    assignee_subject: str | None = Field(
        default=None, alias="assigneeSubject", max_length=128
    )
    snooze_until: datetime | None = Field(default=None, alias="snoozeUntil")
    risk_type: str | None = Field(default=None, alias="riskType", max_length=64)
    model_judgment: str | None = Field(
        default=None, alias="modelJudgment", max_length=32
    )
    expected_lock_version: int | None = Field(
        default=None, alias="expectedLockVersion", ge=1
    )


class InteractionWrite(BaseModel):
    model_version: str = Field(alias="modelVersion", min_length=1, max_length=16)
    sample_id: str = Field(alias="sampleId", min_length=1, max_length=64)
    channel: str = Field(min_length=1, max_length=32)
    contacted_at: datetime = Field(alias="contactedAt")
    note: str | None = Field(default=None, max_length=5000)


class TargetListMember(BaseModel):
    user_id: str = Field(alias="userId", min_length=1, max_length=64)
    sample_id: str = Field(alias="sampleId", min_length=1, max_length=64)


class TargetListWrite(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    decision: str = Field(min_length=1, max_length=64)
    model_version: str = Field(alias="modelVersion", min_length=1, max_length=16)
    target_scope: str | None = Field(default=None, alias="targetScope", pattern="^(region|city)$")
    region_code: str | None = Field(default=None, alias="regionCode", max_length=32)
    city_key: str | None = Field(default=None, alias="cityKey", max_length=128)
    city_name: str | None = Field(default=None, alias="cityName", max_length=128)
    members: list[TargetListMember] = Field(min_length=1, max_length=5000)


class ActionPlanMilestone(BaseModel):
    day_offset: int = Field(alias="dayOffset")
    metric_code: str = Field(alias="metricCode", min_length=1, max_length=64)
    metric_label: str = Field(alias="metricLabel", min_length=1, max_length=128)
    observation_note: str | None = Field(default=None, alias="observationNote", max_length=500)


class ActionPlanWrite(BaseModel):
    plan_type: str = Field(alias="planType", min_length=1, max_length=16)
    model_version: str = Field(alias="modelVersion", min_length=1, max_length=16)
    reviewer_user_id: str | None = Field(default=None, alias="reviewerUserId", max_length=64)
    sample_id: str | None = Field(default=None, alias="sampleId", max_length=64)
    region_code: str | None = Field(default=None, alias="regionCode", max_length=32)
    target_scope: str | None = Field(default=None, alias="targetScope", pattern="^(region|city)$")
    city_key: str | None = Field(default=None, alias="cityKey", max_length=128)
    city_name: str | None = Field(default=None, alias="cityName", max_length=128)
    target_list_id: int | None = Field(default=None, alias="targetListId")
    manager_decision: str | None = Field(default=None, alias="managerDecision", max_length=64)
    action_type: str = Field(alias="actionType", min_length=1, max_length=128)
    message_title: str | None = Field(default=None, alias="messageTitle", max_length=255)
    message_body: str | None = Field(default=None, alias="messageBody", max_length=5000)
    status: str = Field(default="draft", max_length=16)
    channels: list[str] = Field(default_factory=list, max_length=5)
    business_ids: list[str] = Field(default_factory=list, alias="businessIds", max_length=100)
    milestones: list[ActionPlanMilestone] = Field(default_factory=list, max_length=20)
    expected_lock_version: int | None = Field(default=None, alias="expectedLockVersion", ge=1)


class ReviewAlertResolutionWrite(BaseModel):
    status: str = Field(pattern="^(completed|dismissed)$")
    note: str | None = Field(default=None, max_length=2000)


def _service_error(error: Exception) -> HTTPException:
    if isinstance(error, PermissionError):
        return HTTPException(status_code=403, detail=str(error))
    if isinstance(error, RuntimeError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, ValueError):
        return HTTPException(status_code=422, detail=str(error))
    if isinstance(error, IntegrityError):
        return HTTPException(
            status_code=422,
            detail="리뷰어와 모델 표본이 일치하지 않습니다",
        )
    if isinstance(error, OperationalError):
        return HTTPException(
            status_code=503,
            detail="운영 데이터베이스에 연결할 수 없습니다",
        )
    if isinstance(error, ProgrammingError):
        return HTTPException(
            status_code=503,
            detail="운영 데이터 테이블이 아직 적용되지 않았습니다",
        )
    return HTTPException(status_code=500, detail="운영 데이터 처리에 실패했습니다")


def _scope_for_identity(engine, identity: OperatorIdentity) -> tuple[list[str] | None, set[str] | None]:
    regions = regions_for_identity(engine, identity)
    reviewers = reviewer_ids_for_regions(engine, regions) if regions is not None else None
    return regions, reviewers


def _require_reviewer_access(engine, identity: OperatorIdentity, reviewer_user_id: str) -> None:
    _, allowed_reviewers = _scope_for_identity(engine, identity)
    if allowed_reviewers is not None and reviewer_user_id not in allowed_reviewers:
        raise PermissionError("배정된 권역의 핵심 리뷰어만 처리할 수 있습니다")


def _require_region_access(identity: OperatorIdentity, region_code: str | None) -> None:
    if identity.access_role != "OPERATOR":
        return
    normalized = region_code.strip().upper() if region_code else None
    if normalized != identity.region_code:
        raise PermissionError("배정된 권역만 처리할 수 있습니다")


def _normalize_region(region_code: str | None) -> str | None:
    return region_code.strip().upper() if region_code else None


def _scoped_target_lists(
    rows: list[dict],
    allowed_regions: list[str] | None,
    allowed_reviewers: set[str] | None,
) -> list[dict]:
    if allowed_reviewers is None:
        return rows
    scoped = []
    for row in rows:
        if row.get("regionCode") and _normalize_region(row["regionCode"]) not in allowed_regions:
            continue
        members = [user_id for user_id in row["memberUserIds"] if user_id in allowed_reviewers]
        if members:
            scoped.append({**row, "memberUserIds": members, "memberCount": len(members)})
    return scoped


def _scoped_action_plans(
    rows: list[dict],
    allowed_regions: list[str] | None,
    allowed_reviewers: set[str] | None,
) -> list[dict]:
    if allowed_reviewers is None:
        return rows
    return [
        row
        for row in rows
        if (
            row["planType"] == "regional"
            and _normalize_region(row["regionCode"]) in allowed_regions
        )
        or (row["planType"] == "individual" and row["reviewerUserId"] in allowed_reviewers)
    ]


def _require_target_list_access(
    row: dict,
    identity: OperatorIdentity,
    allowed_reviewers: set[str] | None,
) -> None:
    if allowed_reviewers is None:
        return
    _require_region_access(identity, row.get("regionCode") or identity.region_code)
    if any(user_id not in allowed_reviewers for user_id in row["memberUserIds"]):
        raise PermissionError("배정된 권역의 대상 명단만 처리할 수 있습니다")


def _require_action_plan_access(
    row: dict,
    identity: OperatorIdentity,
    allowed_reviewers: set[str] | None,
) -> None:
    if allowed_reviewers is None:
        return
    if row["planType"] == "regional":
        _require_region_access(identity, row.get("regionCode"))
    elif row.get("reviewerUserId") not in allowed_reviewers:
        raise PermissionError("배정된 권역의 실행안만 처리할 수 있습니다")


@router.get("/decisions")
def decisions(
    model_version: str = Query(default="v04", min_length=1, max_length=16),
    identity: OperatorIdentity = Depends(get_current_identity),
) -> dict:
    try:
        engine = get_engine()
        rows = list_decisions(engine, model_version)
        _, allowed_reviewers = _scope_for_identity(engine, identity)
        if allowed_reviewers is not None:
            rows = [row for row in rows if row["reviewerUserId"] in allowed_reviewers]
        return {"items": rows}
    except Exception as error:
        raise _service_error(error) from error


@router.put("/decisions/{reviewer_user_id}")
def put_decision(
    reviewer_user_id: str,
    body: DecisionWrite,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        _require_reviewer_access(get_engine(), operator, reviewer_user_id)
        payload = body.model_dump(by_alias=False)
        return save_decision(get_engine(), reviewer_user_id, payload, operator)
    except Exception as error:
        raise _service_error(error) from error


@router.delete("/decisions/{reviewer_user_id}")
def remove_decision(
    reviewer_user_id: str,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        _require_reviewer_access(get_engine(), operator, reviewer_user_id)
        return {
            "deleted": delete_decision(get_engine(), reviewer_user_id, operator),
            "reviewerUserId": reviewer_user_id,
        }
    except Exception as error:
        raise _service_error(error) from error


@router.get("/decisions/{reviewer_user_id}/history")
def decision_history(
    reviewer_user_id: str,
    identity: OperatorIdentity = Depends(get_current_identity),
) -> dict:
    try:
        _require_reviewer_access(get_engine(), identity, reviewer_user_id)
        return {"items": list_history(get_engine(), reviewer_user_id)}
    except Exception as error:
        raise _service_error(error) from error


@router.get("/reviewers/{reviewer_user_id}/interactions")
def interactions(
    reviewer_user_id: str,
    identity: OperatorIdentity = Depends(get_current_identity),
) -> dict:
    try:
        _require_reviewer_access(get_engine(), identity, reviewer_user_id)
        return {"items": list_interactions(get_engine(), reviewer_user_id)}
    except Exception as error:
        raise _service_error(error) from error


@router.post("/reviewers/{reviewer_user_id}/interactions", status_code=201)
def post_interaction(
    reviewer_user_id: str,
    body: InteractionWrite,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        _require_reviewer_access(get_engine(), operator, reviewer_user_id)
        return add_interaction(
            get_engine(), reviewer_user_id, body.model_dump(by_alias=False), operator
        )
    except Exception as error:
        raise _service_error(error) from error


@router.get("/target-lists")
def target_lists(identity: OperatorIdentity = Depends(get_current_identity)) -> dict:
    try:
        engine = get_engine()
        regions, allowed_reviewers = _scope_for_identity(engine, identity)
        return {
            "items": _scoped_target_lists(
                list_target_lists(engine), regions, allowed_reviewers
            )
        }
    except Exception as error:
        raise _service_error(error) from error


@router.post("/target-lists", status_code=201)
def post_target_list(
    body: TargetListWrite,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        engine = get_engine()
        _require_region_access(operator, body.region_code or operator.region_code)
        _, allowed_reviewers = _scope_for_identity(engine, operator)
        if allowed_reviewers is not None and any(
            member.user_id not in allowed_reviewers for member in body.members
        ):
            raise PermissionError("배정된 권역의 핵심 리뷰어만 대상 명단에 저장할 수 있습니다")
        payload = {
            "name": body.name,
            "decision": body.decision,
            "model_version": body.model_version,
            "target_scope": body.target_scope,
            "region_code": _normalize_region(body.region_code),
            "city_key": body.city_key,
            "city_name": body.city_name,
            "members": [
                {"user_id": member.user_id, "sample_id": member.sample_id}
                for member in body.members
            ],
        }
        return create_target_list(engine, payload, operator)
    except Exception as error:
        raise _service_error(error) from error


@router.delete("/target-lists/{list_id}")
def remove_target_list(
    list_id: int,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        engine = get_engine()
        _, allowed_reviewers = _scope_for_identity(engine, operator)
        existing = next(
            (row for row in list_target_lists(engine) if row["listId"] == list_id),
            None,
        )
        if existing is not None:
            _require_target_list_access(existing, operator, allowed_reviewers)
        return {"deleted": delete_target_list(engine, list_id), "listId": list_id}
    except Exception as error:
        raise _service_error(error) from error


@router.get("/action-plans")
def action_plans(
    plan_type: str | None = Query(default=None, max_length=16),
    identity: OperatorIdentity = Depends(get_current_identity),
) -> dict:
    try:
        engine = get_engine()
        regions, allowed_reviewers = _scope_for_identity(engine, identity)
        return {
            "items": _scoped_action_plans(
                list_action_plans(engine, plan_type), regions, allowed_reviewers
            )
        }
    except Exception as error:
        raise _service_error(error) from error


def _action_payload(body: ActionPlanWrite) -> dict:
    raw = body.model_dump(by_alias=False)
    raw["region_code"] = _normalize_region(raw.get("region_code"))
    raw["business_ids"] = raw.pop("business_ids")
    raw["milestones"] = [item.model_dump(by_alias=False) for item in body.milestones]
    return raw


@router.post("/action-plans", status_code=201)
def post_action_plan(
    body: ActionPlanWrite,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        engine = get_engine()
        if body.plan_type == "regional":
            _require_region_access(operator, body.region_code)
        elif body.reviewer_user_id:
            _require_reviewer_access(engine, operator, body.reviewer_user_id)
        return save_action_plan(engine, _action_payload(body), operator)
    except Exception as error:
        raise _service_error(error) from error


@router.put("/action-plans/{plan_id}")
def put_action_plan(
    plan_id: int,
    body: ActionPlanWrite,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        engine = get_engine()
        _, allowed_reviewers = _scope_for_identity(engine, operator)
        existing = next(
            (row for row in list_action_plans(engine) if row["planId"] == plan_id),
            None,
        )
        if existing is not None:
            _require_action_plan_access(existing, operator, allowed_reviewers)
        if body.plan_type == "regional":
            _require_region_access(operator, body.region_code)
        elif body.reviewer_user_id:
            _require_reviewer_access(engine, operator, body.reviewer_user_id)
        return save_action_plan(engine, _action_payload(body), operator, plan_id)
    except Exception as error:
        raise _service_error(error) from error


@router.get("/operations-history")
def operations_history(
    limit: int = Query(default=200, ge=1, le=500),
    identity: OperatorIdentity = Depends(get_current_identity),
) -> dict:
    try:
        engine = get_engine()
        review_alerts = list_review_alerts(engine, identity, limit)
        due_reviews = list_due_reviews(engine, limit)
        decision_rows = list_all_history(engine, limit)
        interaction_rows = list_all_interactions(engine, limit)
        target_rows = list_target_lists(engine)
        plan_rows = list_action_plans(engine)
        allowed_regions = regions_for_identity(engine, identity)
        if allowed_regions is not None:
            allowed_reviewers = reviewer_ids_for_regions(engine, allowed_regions)
            due_reviews = [row for row in due_reviews if row["reviewerUserId"] in allowed_reviewers]
            decision_rows = [row for row in decision_rows if row["reviewerUserId"] in allowed_reviewers]
            interaction_rows = [row for row in interaction_rows if row["reviewerUserId"] in allowed_reviewers]
            scoped_targets = []
            for row in target_rows:
                scoped_members = [user_id for user_id in row["memberUserIds"] if user_id in allowed_reviewers]
                if scoped_members:
                    scoped_targets.append({**row, "memberUserIds": scoped_members, "memberCount": len(scoped_members)})
            target_rows = scoped_targets
            plan_rows = [
                row for row in plan_rows
                if (row["planType"] == "regional" and row["regionCode"] in allowed_regions)
                or (row["planType"] == "individual" and row["reviewerUserId"] in allowed_reviewers)
            ]
        return {
            "dueReviews": due_reviews,
            "reviewAlerts": review_alerts,
            "decisionHistory": decision_rows,
            "interactions": interaction_rows,
            "targetLists": target_rows,
            "actionPlans": plan_rows,
            "operatorScopes": [
                row for row in list_operator_scopes(engine)
                if allowed_regions is None or row["region"] in allowed_regions
            ],
            "viewer": {
                "subject": identity.subject,
                "name": identity.name,
                "role": identity.access_role,
                "canWrite": identity.access_role in {"ADMIN", "OPERATOR"},
            },
        }
    except Exception as error:
        raise _service_error(error) from error


@router.get("/review-alerts/{alert_id}/history")
def review_alert_history(
    alert_id: int,
    identity: OperatorIdentity = Depends(get_current_identity),
) -> dict:
    try:
        return {"items": list_review_alert_history(get_engine(), alert_id, identity)}
    except Exception as error:
        raise _service_error(error) from error


@router.patch("/review-alerts/{alert_id}")
def patch_review_alert(
    alert_id: int,
    body: ReviewAlertResolutionWrite,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        return resolve_review_alert(
            get_engine(), alert_id, body.status, body.note, operator
        )
    except Exception as error:
        raise _service_error(error) from error
