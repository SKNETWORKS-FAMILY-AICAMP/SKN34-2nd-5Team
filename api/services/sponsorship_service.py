"""Admin CRUD for business_sponsorships (캠페인 스폰서 슬롯).

Read-only business display info (name/city/state) is looked up from the
same interim business parquets regional_service uses for campaign
candidates, so a sponsorship row is meaningful even without joining any
prediction/recommendation table.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALID_STATUSES = ("scheduled", "active", "expired", "cancelled")


@lru_cache(maxsize=1)
def _load_business_names() -> dict[str, dict]:
    interim = PROJECT_ROOT / "data" / "interim"
    columns = ["business_id", "name", "city", "state"]
    frame = pd.concat(
        [
            pd.read_parquet(interim / "restaurant_businesses.parquet", columns=columns),
            pd.read_parquet(interim / "additional_culinary_businesses_v02.parquet", columns=columns),
        ],
        ignore_index=True,
    ).drop_duplicates("business_id", keep="first")
    return {
        str(row.business_id): {"name": row.name, "city": row.city, "state": row.state}
        for row in frame.itertuples(index=False)
    }


def _effective_status(status: str, start_date, end_date) -> str:
    """Return the operator-facing status from the scheduled exposure window."""
    today = date.today()
    if status == "cancelled":
        return "cancelled"
    if status == "expired" or end_date < today:
        return "expired"
    if start_date > today:
        return "scheduled"
    return "active"


def search_sponsorship_businesses(query: str, limit: int = 20) -> list[dict]:
    normalized = query.strip().lower()
    if len(normalized) < 2:
        return []
    matches = [
        {"businessId": business_id, "name": info["name"], "city": info["city"], "state": info["state"]}
        for business_id, info in _load_business_names().items()
        if normalized in " ".join(str(value or "") for value in (business_id, info["name"], info["city"], info["state"])).lower()
    ]
    return sorted(matches, key=lambda item: (item["name"] or "", item["state"] or "", item["city"] or ""))[:limit]


def list_sponsorships(engine: Engine) -> list[dict]:
    with engine.connect() as connection:
        found = int(
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = 'business_sponsorships'"
                )
            ).scalar_one()
        )
        if not found:
            return []
        rows = connection.execute(
            text(
                """
                SELECT sponsorship_id, business_id, region_state, start_date, end_date,
                       priority_tier, status, created_by, created_at
                FROM business_sponsorships
                WHERE status <> 'cancelled'
                ORDER BY start_date ASC, end_date ASC
                """
            )
        ).mappings().all()

    names = _load_business_names()
    result = []
    for row in rows:
        business = names.get(str(row["business_id"]), {})
        result.append(
            {
                "sponsorshipId": int(row["sponsorship_id"]),
                "businessId": row["business_id"],
                "businessName": business.get("name"),
                "businessCity": business.get("city"),
                "regionState": row["region_state"],
                "startDate": row["start_date"].isoformat(),
                "endDate": row["end_date"].isoformat(),
                "priorityTier": int(row["priority_tier"]),
                "status": _effective_status(row["status"], row["start_date"], row["end_date"]),
                "createdBy": row["created_by"],
                "createdAt": row["created_at"].isoformat(),
            }
        )
    return result


def create_sponsorship(
    engine: Engine,
    business_id: str,
    start_date,
    end_date,
    priority_tier: int,
    created_by: str,
) -> dict:
    if end_date < start_date:
        raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
    if end_date < date.today():
        raise ValueError("종료일은 오늘 이후로 선택하세요.")
    business = _load_business_names().get(str(business_id))
    if business is None:
        raise ValueError("등록 가능한 Yelp 매장을 선택하세요.")
    status = _effective_status("active", start_date, end_date)
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO business_sponsorships
                    (business_id, region_state, start_date, end_date, priority_tier, status, created_by)
                VALUES
                    (:business_id, :region_state, :start_date, :end_date, :priority_tier, :status, :created_by)
                """
            ),
            {
                "business_id": str(business_id),
                "region_state": business["state"],
                "start_date": start_date,
                "end_date": end_date,
                "priority_tier": priority_tier,
                "status": status,
                "created_by": created_by,
            },
        )
    sponsorship_id = int(result.lastrowid)
    return next(item for item in list_sponsorships(engine) if item["sponsorshipId"] == sponsorship_id)


def update_sponsorship_status(engine: Engine, sponsorship_id: int, status: str) -> dict | None:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE business_sponsorships SET status = :status "
                "WHERE sponsorship_id = :sponsorship_id"
            ),
            {"status": status, "sponsorship_id": sponsorship_id},
        )
    sponsorships = list_sponsorships(engine)
    return next((row for row in sponsorships if row["sponsorshipId"] == sponsorship_id), None)


def update_sponsorship_schedule(
    engine: Engine,
    sponsorship_id: int,
    start_date,
    end_date,
    priority_tier: int,
) -> dict | None:
    if end_date < start_date:
        raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
    if end_date < date.today():
        raise ValueError("종료일은 오늘 이후로 선택하세요.")
    status = _effective_status("active", start_date, end_date)
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE business_sponsorships
                SET start_date = :start_date,
                    end_date = :end_date,
                    priority_tier = :priority_tier,
                    status = :status
                WHERE sponsorship_id = :sponsorship_id
                  AND status <> 'cancelled'
                """
            ),
            {
                "start_date": start_date,
                "end_date": end_date,
                "priority_tier": priority_tier,
                "status": status,
                "sponsorship_id": sponsorship_id,
            },
        )
    if result.rowcount == 0:
        return None
    return next(item for item in list_sponsorships(engine) if item["sponsorshipId"] == sponsorship_id)


def cancel_scheduled_sponsorship(engine: Engine, sponsorship_id: int) -> dict | None:
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT status, start_date, end_date
                FROM business_sponsorships
                WHERE sponsorship_id = :sponsorship_id
                FOR UPDATE
                """
            ),
            {"sponsorship_id": sponsorship_id},
        ).mappings().first()
        if row is None:
            return None
        if _effective_status(row["status"], row["start_date"], row["end_date"]) != "scheduled":
            raise ValueError("노출 예정 상태인 등록만 취소할 수 있습니다.")
        connection.execute(
            text(
                "UPDATE business_sponsorships SET status = 'cancelled' "
                "WHERE sponsorship_id = :sponsorship_id"
            ),
            {"sponsorship_id": sponsorship_id},
        )
    return {"sponsorshipId": sponsorship_id, "status": "cancelled"}


def reactivate_sponsorship(engine: Engine, sponsorship_id: int, days: int = 30) -> dict | None:
    """Reactivate an expired sponsorship and roll its window to start today.

    Flipping status alone would leave a past end_date, which the campaign
    query's CURDATE() BETWEEN check would silently exclude — so reactivating
    must also move the window forward, not just the status.
    """
    if days <= 0:
        raise ValueError("days must be positive")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE business_sponsorships
                SET status = 'active',
                    start_date = CURDATE(),
                    end_date = DATE_ADD(CURDATE(), INTERVAL :days DAY)
                WHERE sponsorship_id = :sponsorship_id
                """
            ),
            {"days": days, "sponsorship_id": sponsorship_id},
        )
    sponsorships = list_sponsorships(engine)
    return next((row for row in sponsorships if row["sponsorshipId"] == sponsorship_id), None)
