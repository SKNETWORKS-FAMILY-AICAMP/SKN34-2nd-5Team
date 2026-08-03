"""Serve local Yelp Open Dataset photo files by validated photo ID."""
from __future__ import annotations

from pathlib import Path
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter(prefix="/api", tags=["business-photos"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHOTO_DIR = PROJECT_ROOT / "data" / "photos" / "photos"
PHOTO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@router.get("/business-photos/{photo_id}")
def business_photo(photo_id: str) -> FileResponse:
    if not PHOTO_ID_PATTERN.fullmatch(photo_id):
        raise HTTPException(status_code=404, detail="photo not found")
    path = PHOTO_DIR / f"{photo_id}.jpg"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="photo not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
