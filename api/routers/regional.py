from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from api.db import get_engine
from api.services.regional_service import (
    get_regional_campaign_restaurants,
    get_regional_radius,
    get_regional_summary,
)
from api.services.city_operation_service import get_city_operating_context

router = APIRouter(prefix="/api", tags=["regional"])


class RegionalCampaignRestaurantRequest(BaseModel):
    region: str = Field(min_length=2, max_length=8)
    sample_ids: list[str] = Field(min_length=1, max_length=5000)


@router.get("/regional")
def regional() -> dict:
    return get_regional_summary(get_engine())


@router.get("/regional/cities")
def regional_cities(
    selection_year: int = Query(default=2018, ge=2009, le=2018),
) -> dict:
    return get_city_operating_context(get_engine(), selection_year)


@router.get("/regional/radius")
def regional_radius() -> dict:
    return get_regional_radius(get_engine())


@router.post("/regional/campaign-restaurants")
def regional_campaign_restaurants(body: RegionalCampaignRestaurantRequest) -> dict:
    return get_regional_campaign_restaurants(
        get_engine(), body.region, body.sample_ids
    )
