"""Optional Yelp Open Dataset photos for recommendation businesses."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine


TABLE_NAME = "business_photo"


def get_business_photos(
    engine: Engine, business_ids: list[str], limit_per_business: int = 3
) -> dict[str, list[dict]]:
    unique_ids = list(dict.fromkeys(str(value) for value in business_ids if value))
    if not unique_ids:
        return {}
    statement = text(
        """
        SELECT business_id, photo_id, label, caption, display_rank
        FROM business_photo
        WHERE business_id IN :business_ids
        ORDER BY business_id, display_rank
        """
    ).bindparams(bindparam("business_ids", expanding=True))
    with engine.connect() as connection:
        available = int(
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = :table_name"
                ),
                {"table_name": TABLE_NAME},
            ).scalar_one()
        )
        if not available:
            return {}
        rows = connection.execute(
            statement, {"business_ids": unique_ids}
        ).mappings().all()

    photos: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        business_id = str(row["business_id"])
        if len(photos[business_id]) >= limit_per_business:
            continue
        photo_id = str(row["photo_id"])
        photos[business_id].append(
            {
                "photoId": photo_id,
                "label": row["label"],
                "caption": row["caption"],
                "displayRank": int(row["display_rank"]),
                "path": f"/api/business-photos/{photo_id}",
                "sourceType": "yelp_open_dataset_photos_2022",
            }
        )
    return dict(photos)
