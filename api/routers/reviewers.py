from __future__ import annotations

from fastapi import APIRouter

from api.db import get_engine
from api.services.reviewer_service import get_reviewers

router = APIRouter(prefix="/api", tags=["reviewers"])


@router.get("/reviewers")
def reviewers() -> list[dict]:
    return get_reviewers(get_engine())
