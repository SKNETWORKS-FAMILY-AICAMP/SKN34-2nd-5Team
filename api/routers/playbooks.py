from __future__ import annotations

from fastapi import APIRouter

from api.db import get_engine
from api.services.playbooks_service import get_playbooks

router = APIRouter(prefix="/api", tags=["playbooks"])


@router.get("/playbooks")
def playbooks() -> list[dict]:
    return get_playbooks(get_engine())
