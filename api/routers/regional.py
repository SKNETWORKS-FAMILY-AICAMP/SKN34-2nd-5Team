from __future__ import annotations

from fastapi import APIRouter

from api.db import get_engine
from api.services.regional_service import get_regional_summary

router = APIRouter(prefix="/api", tags=["regional"])


@router.get("/regional")
def regional() -> dict:
    return get_regional_summary(get_engine())
