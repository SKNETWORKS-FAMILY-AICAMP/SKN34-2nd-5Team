"""Reviewer 360 리뷰 활동 반경 도구 데이터 (A-8, work-spec G-5).

reviewer_spatial_summary(MySQL, 중심점·P90 반경)와 방문 음식점 개별 좌표
(로컬 parquet, data/processed/spatial/)를 결합한다. 방문 음식점 목록은
리뷰어 단건 조회에서만 필요한 대용량 데이터라 MySQL에 올리지 않고
읽기 전용으로 pipeline/v04/build_spatial_v04.py의 출력 parquet에서 직접
읽는다.

좌표 투영: 위경도를 그대로 x/y로 쓰면 미국 중위도에서 동서 거리가
왜곡된다(경도 1도 폭이 위도 1도의 0.75~0.8배). 대신 정확한 haversine
거리·방위각을 계산해 극좌표로 반환하고, 프런트에서
x = distance*sin(bearing), y = -distance*cos(bearing) 로 변환한다.
docs/ui/V05_WORK_SPEC.md 9.2절(확정)의 좌표 투영 결정.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from api.services.business_attribute_service import get_business_display_attributes
from api.services.business_photo_service import get_business_photos

MODEL_VERSION = "v05_05_dl"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EARTH_RADIUS_KM = 6371.0
MAP_COORDINATE_PRECISION = 1


def _haversine_distance_bearing(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> tuple[float, float]:
    """(point1 -> point2) 거리(km)와 방위각(도, 북=0 시계방향)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    distance = 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, a)))

    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(
        dlambda
    )
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
    return distance, bearing


@lru_cache(maxsize=1)
def _load_activity_with_business_names() -> pd.DataFrame:
    spatial_dir = PROJECT_ROOT / "data" / "processed" / "spatial"
    businesses = pd.read_parquet(
        spatial_dir / "business_locations_v04.parquet",
        columns=["business_id", "name", "city", "state", "latitude", "longitude"],
    )
    activity = pd.read_parquet(
        spatial_dir / "reviewer_activity_locations_v04.parquet",
        columns=["sample_id", "period_type", "business_id", "review_count"],
    )
    interim_dir = PROJECT_ROOT / "data" / "interim"
    metadata_columns = ["business_id", "stars", "review_count", "categories"]
    metadata_paths = [
        interim_dir / "restaurant_businesses.parquet",
        interim_dir / "additional_culinary_businesses_v02.parquet",
    ]
    metadata_frames = [
        pd.read_parquet(path, columns=metadata_columns)
        for path in metadata_paths
        if path.is_file()
    ]
    metadata = (
        pd.concat(metadata_frames, ignore_index=True)
        if metadata_frames
        else pd.DataFrame(columns=metadata_columns)
    ).drop_duplicates("business_id", keep="first")
    metadata = metadata.rename(columns={"review_count": "dataset_review_count"})
    return activity.merge(businesses, on="business_id", how="left").merge(
        metadata, on="business_id", how="left"
    )


def _region_map_payload(points: pd.DataFrame) -> dict | None:
    """Return city/zone-level geography only; never expose venue coordinates."""
    valid = points.dropna(subset=["city", "latitude", "longitude"]).copy()
    if valid.empty:
        return None

    city_groups = (
        valid.groupby("city", as_index=False)
        .agg(
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
            review_count=("review_count", "sum"),
            venue_count=("business_id", "nunique"),
        )
        .sort_values(["review_count", "venue_count", "city"], ascending=[False, False, True])
    )
    primary_row = city_groups.iloc[0]

    def city_payload(row: pd.Series) -> dict:
        return {
            "city": str(row.city),
            "latitude": round(float(row.latitude), MAP_COORDINATE_PRECISION),
            "longitude": round(float(row.longitude), MAP_COORDINATE_PRECISION),
            "reviewCount": int(row.review_count),
            "venueCount": int(row.venue_count),
        }

    primary = city_payload(primary_row)
    satellites = []
    for _, row in city_groups.iloc[1:4].iterrows():
        item = city_payload(row)
        distance, _ = _haversine_distance_bearing(
            primary["latitude"], primary["longitude"], item["latitude"], item["longitude"]
        )
        item["distanceFromPrimaryKm"] = round(distance)
        satellites.append(item)

    # A 0.1-degree grid deliberately generalizes the primary-city points for
    # the inset. It conveys concentration without returning venues or their
    # precise locations.
    primary_city_points = valid[valid["city"] == primary_row.city].copy()
    primary_city_points["zone_lat"] = primary_city_points["latitude"].round(MAP_COORDINATE_PRECISION)
    primary_city_points["zone_lon"] = primary_city_points["longitude"].round(MAP_COORDINATE_PRECISION)
    zones = (
        primary_city_points.groupby(["zone_lat", "zone_lon"], as_index=False)
        .agg(review_count=("review_count", "sum"), venue_count=("business_id", "nunique"))
        .sort_values(["review_count", "venue_count"], ascending=False)
        .head(6)
    )

    return {
        "primaryRegion": primary,
        "satelliteRegions": satellites,
        "additionalRegionCount": max(0, len(city_groups) - 1 - len(satellites)),
        "primaryZones": [
            {
                "latitude": float(row.zone_lat),
                "longitude": float(row.zone_lon),
                "reviewCount": int(row.review_count),
                "venueCount": int(row.venue_count),
            }
            for _, row in zones.iterrows()
        ],
    }


def _period_payload(
    summary: dict,
    points: pd.DataFrame,
    display_attributes: dict[str, dict],
    business_photos: dict[str, list[dict]],
) -> dict:
    if not summary["radius_available"]:
        return {"available": False, "activityYear": int(summary["activity_year"])}

    center_lat = summary["center_latitude"]
    center_lon = summary["center_longitude"]

    businesses = []
    for row in points.itertuples():
        if pd.isna(row.latitude) or pd.isna(row.longitude):
            continue
        distance, bearing = _haversine_distance_bearing(
            center_lat, center_lon, row.latitude, row.longitude
        )
        businesses.append(
            {
                "businessId": str(row.business_id),
                "name": row.name,
                "city": row.city,
                "state": row.state,
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "reviewCount": int(row.review_count),
                "stars": float(row.stars) if pd.notna(row.stars) else None,
                "datasetReviewCount": (
                    int(row.dataset_review_count)
                    if pd.notna(row.dataset_review_count)
                    else None
                ),
                "categories": [
                    label.strip()
                    for label in (
                        str(row.categories) if pd.notna(row.categories) else ""
                    ).split(",")
                    if label.strip()
                ],
                "distanceKm": round(distance, 2),
                "bearingDeg": round(bearing, 1),
                "displayAttributes": display_attributes.get(str(row.business_id)),
                "photos": business_photos.get(str(row.business_id), []),
                "yelpSearchUrl": (
                    "https://www.yelp.com/search?find_desc="
                    f"{quote_plus(str(row.name))}&find_loc="
                    f"{quote_plus(f'{row.city}, {row.state}') }"
                ),
            }
        )
    businesses.sort(key=lambda b: b["distanceKm"])

    return {
        "available": True,
        "activityYear": int(summary["activity_year"]),
        "p90RadiusKm": round(summary["p90_radius_km"], 2),
        "businesses": businesses,
        "mapRegions": _region_map_payload(points),
    }


def get_reviewer_radius(engine: Engine, user_id: str) -> dict | None:
    with engine.connect() as conn:
        sample_row = conn.execute(
            text(
                "SELECT sample_id FROM cohort_samples "
                "WHERE model_version = :v AND user_id = :u "
                "AND split_v04 = 'test' AND selection_year = 2018"
            ),
            {"v": MODEL_VERSION, "u": user_id},
        ).first()
        if sample_row is None:
            return None
        sample_id = sample_row.sample_id

        summary_rows = conn.execute(
            text(
                """
                SELECT period_type, activity_year, center_latitude,
                       center_longitude, p90_radius_km, radius_available,
                       radius_change_km, radius_change_rate, center_shift_km
                FROM reviewer_spatial_summary
                WHERE model_version = :v AND sample_id = :s
                """
            ),
            {"v": MODEL_VERSION, "s": sample_id},
        ).mappings().all()

    if not summary_rows:
        return {"available": False}

    summaries = {row["period_type"]: dict(row) for row in summary_rows}
    activity = _load_activity_with_business_names()
    reviewer_rows = activity[activity["sample_id"] == sample_id]
    business_ids = reviewer_rows["business_id"].dropna().astype(str).unique().tolist()
    display_attributes = get_business_display_attributes(engine, business_ids)
    business_photos = get_business_photos(engine, business_ids)

    periods = {}
    for period_type, summary in summaries.items():
        period_points = reviewer_rows[reviewer_rows["period_type"] == period_type]
        periods[period_type] = _period_payload(
            summary, period_points, display_attributes, business_photos
        )

    selection = summaries.get("selection")
    change = None
    if selection is not None and selection.get("radius_change_km") is not None:
        change = {
            "radiusChangeKm": round(selection["radius_change_km"], 2),
            "radiusChangeRate": (
                round(selection["radius_change_rate"], 4)
                if selection["radius_change_rate"] is not None
                else None
            ),
            "centerShiftKm": (
                round(selection["center_shift_km"], 2)
                if selection["center_shift_km"] is not None
                else None
            ),
        }

    return {
        "available": True,
        "comparison": periods.get("comparison", {"available": False}),
        "selection": periods.get("selection", {"available": False}),
        "change": change,
    }
