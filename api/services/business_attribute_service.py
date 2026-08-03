"""Optional display context for Yelp Open Dataset restaurant candidates."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection, Engine


TABLE_NAME = "business_display_attribute"


def _table_available(connection: Connection) -> bool:
    return bool(
        connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = :table_name"
            ),
            {"table_name": TABLE_NAME},
        ).scalar_one()
    )


def _json_value(value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _optional_bool(value: Any) -> bool | None:
    return None if value is None else bool(value)


def _serialize(row: dict) -> dict:
    parking = _json_value(row["parking_json"])
    return {
        "address": row["address"],
        "postalCode": row["postal_code"],
        "isOpenSnapshot": bool(row["is_open_snapshot"]),
        "hours": _json_value(row["hours_json"]),
        "priceRange": int(row["price_range"]) if row["price_range"] is not None else None,
        "takeout": _optional_bool(row["takeout"]),
        "delivery": _optional_bool(row["delivery"]),
        "reservations": _optional_bool(row["reservations"]),
        "outdoorSeating": _optional_bool(row["outdoor_seating"]),
        "wifi": row["wifi"],
        "parking": [key for key, available in (parking or {}).items() if available],
        "wheelchairAccessible": _optional_bool(row["wheelchair_accessible"]),
        "alcohol": row["alcohol"],
        "sourceType": row["source_type"],
    }


def get_business_display_attributes(
    engine: Engine, business_ids: list[str]
) -> dict[str, dict]:
    unique_ids = list(dict.fromkeys(str(value) for value in business_ids if value))
    if not unique_ids:
        return {}

    statement = text(
        """
        SELECT business_id, address, postal_code, is_open_snapshot, hours_json,
               price_range, takeout, delivery, reservations, outdoor_seating,
               wifi, parking_json, wheelchair_accessible, alcohol, source_type
        FROM business_display_attribute
        WHERE business_id IN :business_ids
        """
    ).bindparams(bindparam("business_ids", expanding=True))

    with engine.connect() as connection:
        if not _table_available(connection):
            return {}
        rows = connection.execute(
            statement, {"business_ids": unique_ids}
        ).mappings().all()
    return {str(row["business_id"]): _serialize(row) for row in rows}
