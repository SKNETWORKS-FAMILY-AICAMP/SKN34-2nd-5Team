from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from api.auth_context import OperatorIdentity, get_current_operator
from api.db import get_engine
from api.services.retention_operation_service import (
    add_interaction,
    delete_decision,
    list_decisions,
    list_history,
    list_interactions,
    save_decision,
)
from api.services.target_list_service import (
    create_target_list,
    delete_target_list,
    list_target_lists,
)


router = APIRouter(prefix="/api/retention", tags=["retention-operations"])


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
    members: list[TargetListMember] = Field(min_length=1, max_length=5000)


def _service_error(error: Exception) -> HTTPException:
    if isinstance(error, RuntimeError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, ValueError):
        return HTTPException(status_code=422, detail=str(error))
    if isinstance(error, IntegrityError):
        return HTTPException(
            status_code=422,
            detail="리뷰어와 모델 표본이 일치하지 않습니다",
        )
    if isinstance(error, (OperationalError, ProgrammingError)):
        return HTTPException(
            status_code=503,
            detail="운영 데이터 테이블이 아직 적용되지 않았습니다",
        )
    return HTTPException(status_code=500, detail="운영 데이터 처리에 실패했습니다")


@router.get("/decisions")
def decisions(model_version: str = Query(default="v04", min_length=1, max_length=16)) -> dict:
    try:
        return {"items": list_decisions(get_engine(), model_version)}
    except Exception as error:
        raise _service_error(error) from error


@router.put("/decisions/{reviewer_user_id}")
def put_decision(
    reviewer_user_id: str,
    body: DecisionWrite,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
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
        return {
            "deleted": delete_decision(get_engine(), reviewer_user_id, operator),
            "reviewerUserId": reviewer_user_id,
        }
    except Exception as error:
        raise _service_error(error) from error


@router.get("/decisions/{reviewer_user_id}/history")
def decision_history(reviewer_user_id: str) -> dict:
    try:
        return {"items": list_history(get_engine(), reviewer_user_id)}
    except Exception as error:
        raise _service_error(error) from error


@router.get("/reviewers/{reviewer_user_id}/interactions")
def interactions(reviewer_user_id: str) -> dict:
    try:
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
        return add_interaction(
            get_engine(), reviewer_user_id, body.model_dump(by_alias=False), operator
        )
    except Exception as error:
        raise _service_error(error) from error


@router.get("/target-lists")
def target_lists() -> dict:
    try:
        return {"items": list_target_lists(get_engine())}
    except Exception as error:
        raise _service_error(error) from error


@router.post("/target-lists", status_code=201)
def post_target_list(
    body: TargetListWrite,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        payload = {
            "name": body.name,
            "decision": body.decision,
            "model_version": body.model_version,
            "members": [
                {"user_id": member.user_id, "sample_id": member.sample_id}
                for member in body.members
            ],
        }
        return create_target_list(get_engine(), payload, operator)
    except Exception as error:
        raise _service_error(error) from error


@router.delete("/target-lists/{list_id}")
def remove_target_list(
    list_id: int,
    operator: OperatorIdentity = Depends(get_current_operator),
) -> dict:
    try:
        return {"deleted": delete_target_list(get_engine(), list_id), "listId": list_id}
    except Exception as error:
        raise _service_error(error) from error
