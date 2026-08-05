from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.auth_context import OperatorIdentity, get_current_identity
from api.db import get_engine
from api.services.sponsorship_service import (
    cancel_scheduled_sponsorship,
    create_sponsorship,
    list_sponsorships,
    reactivate_sponsorship,
    search_sponsorship_businesses,
    update_sponsorship_schedule,
    update_sponsorship_status,
)


router = APIRouter(prefix="/api/sponsorships", tags=["sponsorships"])


def require_admin(
    identity: OperatorIdentity = Depends(get_current_identity),
) -> OperatorIdentity:
    if identity.access_role != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자만 접근할 수 있습니다.")
    return identity


class SponsorshipStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=16)


class SponsorshipCreate(BaseModel):
    business_id: str = Field(alias="businessId", min_length=1, max_length=64)
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    priority_tier: int = Field(default=1, alias="priorityTier", ge=1, le=9)


class SponsorshipScheduleUpdate(BaseModel):
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    priority_tier: int = Field(default=1, alias="priorityTier", ge=1, le=9)


@router.get("")
def sponsorships(admin: OperatorIdentity = Depends(require_admin)) -> dict:
    return {"sponsorships": list_sponsorships(get_engine())}


@router.get("/businesses")
def sponsorship_businesses(
    q: str = Query(min_length=2, max_length=120),
    admin: OperatorIdentity = Depends(require_admin),
) -> dict:
    return {"businesses": search_sponsorship_businesses(q)}


@router.post("")
def create(
    body: SponsorshipCreate,
    admin: OperatorIdentity = Depends(require_admin),
) -> dict:
    try:
        return create_sponsorship(
            get_engine(),
            body.business_id,
            body.start_date,
            body.end_date,
            body.priority_tier,
            admin.user_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.patch("/{sponsorship_id}/schedule")
def update_schedule(
    sponsorship_id: int,
    body: SponsorshipScheduleUpdate,
    admin: OperatorIdentity = Depends(require_admin),
) -> dict:
    try:
        updated = update_sponsorship_schedule(
            get_engine(),
            sponsorship_id,
            body.start_date,
            body.end_date,
            body.priority_tier,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if updated is None:
        raise HTTPException(status_code=404, detail="스폰서십을 찾을 수 없습니다.")
    return updated


@router.post("/{sponsorship_id}/cancel")
def cancel_registration(
    sponsorship_id: int,
    admin: OperatorIdentity = Depends(require_admin),
) -> dict:
    try:
        cancelled = cancel_scheduled_sponsorship(get_engine(), sponsorship_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if cancelled is None:
        raise HTTPException(status_code=404, detail="스폰서십을 찾을 수 없습니다.")
    return cancelled


@router.patch("/{sponsorship_id}")
def update_sponsorship(
    sponsorship_id: int,
    body: SponsorshipStatusUpdate,
    admin: OperatorIdentity = Depends(require_admin),
) -> dict:
    try:
        updated = update_sponsorship_status(get_engine(), sponsorship_id, body.status)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if updated is None:
        raise HTTPException(status_code=404, detail="스폰서십을 찾을 수 없습니다.")
    return updated


@router.post("/{sponsorship_id}/reactivate")
def reactivate(
    sponsorship_id: int,
    admin: OperatorIdentity = Depends(require_admin),
) -> dict:
    updated = reactivate_sponsorship(get_engine(), sponsorship_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="스폰서십을 찾을 수 없습니다.")
    return updated
