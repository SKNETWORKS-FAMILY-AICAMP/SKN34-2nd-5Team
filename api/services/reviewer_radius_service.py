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

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

MODEL_VERSION = "v04"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EARTH_RADIUS_KM = 6371.0


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
        columns=["business_id", "name", "city", "latitude", "longitude"],
    )
    activity = pd.read_parquet(
        spatial_dir / "reviewer_activity_locations_v04.parquet",
        columns=["sample_id", "period_type", "business_id", "review_count"],
    )
    return activity.merge(businesses, on="business_id", how="left")


def _period_payload(summary: dict, points: pd.DataFrame) -> dict:
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
                "name": row.name,
                "city": row.city,
                "reviewCount": int(row.review_count),
                "distanceKm": round(distance, 2),
                "bearingDeg": round(bearing, 1),
            }
        )
    businesses.sort(key=lambda b: b["distanceKm"])

    return {
        "available": True,
        "activityYear": int(summary["activity_year"]),
        "p90RadiusKm": round(summary["p90_radius_km"], 2),
        "businesses": businesses,
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

    periods = {}
    for period_type, summary in summaries.items():
        period_points = reviewer_rows[reviewer_rows["period_type"] == period_type]
        periods[period_type] = _period_payload(summary, period_points)

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
