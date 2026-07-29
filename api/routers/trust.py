from __future__ import annotations

from fastapi import APIRouter

from api.db import get_engine
from api.services.trust_service import get_trust_data

router = APIRouter(prefix="/api", tags=["trust"])


@router.get("/trust")
def trust() -> dict:
    return get_trust_data(get_engine())
