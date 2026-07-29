from __future__ import annotations

from fastapi import APIRouter

from api.db import get_engine
from api.services.reviewer_detail_service import get_reviewer_details

router = APIRouter(prefix="/api", tags=["reviewer-details"])


@router.get("/reviewer-details")
def reviewer_details() -> dict:
    return get_reviewer_details(get_engine())
