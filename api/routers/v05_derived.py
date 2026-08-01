from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.db import get_engine
from api.services.v05_derived_service import (
    get_regional_derived_context,
    get_reviewer_recommendations,
)


router = APIRouter(prefix="/api", tags=["v05-derived"])


@router.get("/reviewer-details/{user_id}/recommendations")
def reviewer_recommendations(user_id: str) -> dict:
    result = get_reviewer_recommendations(get_engine(), user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="리뷰어를 찾을 수 없습니다")
    return result


@router.get("/regional/derived-context")
def regional_derived_context(
    selection_year: int = Query(default=2018, ge=2009, le=2018),
) -> dict:
    return get_regional_derived_context(get_engine(), selection_year)
