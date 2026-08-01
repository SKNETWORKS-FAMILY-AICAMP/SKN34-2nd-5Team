from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.db import get_engine
from api.services.reviewer_radius_service import get_reviewer_radius

router = APIRouter(prefix="/api", tags=["reviewer-radius"])


@router.get("/reviewer-details/{user_id}/radius")
def reviewer_radius(user_id: str) -> dict:
    result = get_reviewer_radius(get_engine(), user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="리뷰어를 찾을 수 없습니다")
    return result
