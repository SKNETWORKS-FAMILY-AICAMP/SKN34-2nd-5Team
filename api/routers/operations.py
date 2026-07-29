from __future__ import annotations

from fastapi import APIRouter

from api.db import get_engine
from api.services.operations_service import get_operations_summary

router = APIRouter(prefix="/api", tags=["operations"])


@router.get("/operations")
def operations() -> dict:
    return get_operations_summary(get_engine())
