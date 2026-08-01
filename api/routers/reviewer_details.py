from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.db import get_engine
from api.services.reviewer_detail_service import get_reviewer_detail

router = APIRouter(prefix="/api", tags=["reviewer-details"])


@router.get("/reviewer-details/{user_id}")
def reviewer_detail(user_id: str) -> dict:
    detail = get_reviewer_detail(get_engine(), user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="리뷰어를 찾을 수 없습니다")
    return detail
