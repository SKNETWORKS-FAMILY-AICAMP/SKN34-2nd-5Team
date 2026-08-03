"""Derive display-only business attributes for v05 restaurant candidates.

The Yelp Open Dataset is a historical snapshot. These fields are therefore
presentation context only: they must not be described as live opening status,
current hours, or current service availability. The script reads existing raw
and recommendation artifacts without changing them and writes a compact,
reproducible Parquet file for database loading.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_BUSINESS_PATH = ROOT / "data" / "raw" / "yelp_academic_dataset_business.json"
RECOMMENDATION_PATH = (
    ROOT / "data" / "processed" / "reviewer_restaurant_recommendations_v05.parquet"
)
ACTIVITY_PATH = (
    ROOT / "data" / "processed" / "spatial" / "reviewer_activity_locations_v04.parquet"
)
OUTPUT_PATH = ROOT / "data" / "processed" / "business_display_attributes_v01.parquet"
SOURCE_TYPE = "yelp_open_dataset"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build display-only Yelp business attributes for v05."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing derived artifact after explicit approval.",
    )
    return parser.parse_args()


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def parse_literal(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value.strip().strip("\"'")


def parse_enum(value: Any) -> str | None:
    parsed = parse_literal(value)
    if parsed is None:
        return None
    normalized = str(parsed).strip()
    return normalized if normalized and normalized.lower() != "none" else None


def parse_price_range(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if 1 <= parsed <= 4 else None


def parse_parking(value: Any) -> dict[str, bool] | None:
    parsed = parse_literal(value)
    if not isinstance(parsed, dict):
        return None
    normalized = {
        str(key): bool(flag)
        for key, flag in parsed.items()
        if isinstance(flag, bool)
    }
    return normalized or None


def build_row(business: dict[str, Any]) -> dict[str, Any]:
    attributes = business.get("attributes") or {}
    hours = business.get("hours") or None
    parking = parse_parking(attributes.get("BusinessParking"))
    return {
        "business_id": business["business_id"],
        "address": business.get("address") or None,
        "postal_code": business.get("postal_code") or None,
        "is_open_snapshot": bool(business.get("is_open")),
        "hours_json": json.dumps(hours, ensure_ascii=False, sort_keys=True) if hours else None,
        "price_range": parse_price_range(attributes.get("RestaurantsPriceRange2")),
        "takeout": parse_bool(attributes.get("RestaurantsTakeOut")),
        "delivery": parse_bool(attributes.get("RestaurantsDelivery")),
        "reservations": parse_bool(attributes.get("RestaurantsReservations")),
        "outdoor_seating": parse_bool(attributes.get("OutdoorSeating")),
        "wifi": parse_enum(attributes.get("WiFi")),
        "parking_json": json.dumps(parking, sort_keys=True) if parking else None,
        "wheelchair_accessible": parse_bool(attributes.get("WheelchairAccessible")),
        "alcohol": parse_enum(attributes.get("Alcohol")),
        "source_type": SOURCE_TYPE,
    }


def main() -> int:
    args = parse_args()
    if OUTPUT_PATH.exists() and not args.overwrite:
        raise FileExistsError(
            f"{OUTPUT_PATH} already exists; rerun with --overwrite only after approval"
        )
    if not RAW_BUSINESS_PATH.is_file():
        raise FileNotFoundError(RAW_BUSINESS_PATH)
    if not RECOMMENDATION_PATH.is_file():
        raise FileNotFoundError(RECOMMENDATION_PATH)
    if not ACTIVITY_PATH.is_file():
        raise FileNotFoundError(ACTIVITY_PATH)

    recommendations = pd.read_parquet(RECOMMENDATION_PATH, columns=["business_id"])
    activity = pd.read_parquet(ACTIVITY_PATH, columns=["business_id"])
    target_ids = set(recommendations["business_id"].dropna().astype(str)).union(
        activity["business_id"].dropna().astype(str)
    )
    rows: list[dict[str, Any]] = []

    with RAW_BUSINESS_PATH.open("r", encoding="utf-8") as source:
        for line in source:
            business = json.loads(line)
            if business.get("business_id") in target_ids:
                rows.append(build_row(business))

    result = pd.DataFrame(rows).sort_values("business_id", kind="mergesort")
    if result["business_id"].duplicated().any():
        raise ValueError("duplicate business_id in derived display attributes")
    matched_ids = set(result["business_id"])
    missing = sorted(target_ids - matched_ids)
    if missing:
        raise ValueError(f"raw business data is missing {len(missing):,} recommendation IDs")
    if len(result) != len(target_ids):
        raise ValueError(f"derived {len(result):,} rows, expected {len(target_ids):,}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT_PATH, index=False)
    print(
        f"wrote {len(result):,} business display rows to {OUTPUT_PATH}; "
        f"hours={result['hours_json'].notna().sum():,}, "
        f"price={result['price_range'].notna().sum():,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
