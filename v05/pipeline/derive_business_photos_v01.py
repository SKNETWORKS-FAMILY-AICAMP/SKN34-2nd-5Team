"""Derive a deterministic photo manifest for recommended Yelp businesses."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHOTO_ROOT = ROOT / "data" / "photos"
PHOTO_DIR = PHOTO_ROOT / "photos"
PHOTO_METADATA = PHOTO_ROOT / "photos.json"
RECOMMENDATION_PATH = (
    ROOT / "data" / "processed" / "reviewer_restaurant_recommendations_v05.parquet"
)
ACTIVITY_PATH = (
    ROOT / "data" / "processed" / "spatial" / "reviewer_activity_locations_v04.parquet"
)
OUTPUT_PATH = ROOT / "data" / "processed" / "business_photos_v01.parquet"
SOURCE_TYPE = "yelp_open_dataset_photos_2022"
LABEL_PRIORITY = {"food": 0, "outside": 1, "inside": 2, "drink": 3, "menu": 4}


def preferred_row(current: dict | None, candidate: dict) -> dict:
    if current is None:
        return candidate
    current_priority = LABEL_PRIORITY.get(current.get("label"), 99)
    candidate_priority = LABEL_PRIORITY.get(candidate.get("label"), 99)
    if candidate_priority < current_priority:
        return candidate
    return current


def ordered_photos(rows: list[dict]) -> list[dict]:
    by_label: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)
    for values in by_label.values():
        values.sort(key=lambda item: (not bool(item["caption"]), item["photo_id"]))

    ordered: list[dict] = []
    for label, _ in sorted(LABEL_PRIORITY.items(), key=lambda item: item[1]):
        if by_label[label]:
            ordered.append(by_label[label].pop(0))
    remaining = [row for values in by_label.values() for row in values]
    remaining.sort(
        key=lambda item: (
            LABEL_PRIORITY.get(item["label"], 99),
            not bool(item["caption"]),
            item["photo_id"],
        )
    )
    return ordered + remaining


def main() -> None:
    if not PHOTO_METADATA.is_file() or not PHOTO_DIR.is_dir():
        raise FileNotFoundError("data/photos/photos.json and data/photos/photos are required")
    recommendations = pd.read_parquet(RECOMMENDATION_PATH, columns=["business_id"])
    activity = pd.read_parquet(ACTIVITY_PATH, columns=["business_id"])
    target_ids = set(recommendations["business_id"].dropna().astype(str)).union(
        activity["business_id"].dropna().astype(str)
    )

    unique_photos: dict[str, dict] = {}
    with PHOTO_METADATA.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            business_id = str(raw.get("business_id") or "")
            photo_id = str(raw.get("photo_id") or "")
            label = str(raw.get("label") or "unknown").lower()
            if business_id not in target_ids or not photo_id:
                continue
            if not (PHOTO_DIR / f"{photo_id}.jpg").is_file():
                continue
            candidate = {
                "business_id": business_id,
                "photo_id": photo_id,
                "label": label,
                "caption": str(raw.get("caption") or "").strip() or None,
            }
            unique_photos[photo_id] = preferred_row(unique_photos.get(photo_id), candidate)

    by_business: dict[str, list[dict]] = defaultdict(list)
    for row in unique_photos.values():
        by_business[row["business_id"]].append(row)

    output = []
    for business_id in sorted(by_business):
        for display_rank, row in enumerate(ordered_photos(by_business[business_id]), start=1):
            output.append(
                {
                    "business_id": business_id,
                    "photo_id": row["photo_id"],
                    "label": row["label"],
                    "caption": row["caption"],
                    "display_rank": display_rank,
                    "source_type": SOURCE_TYPE,
                }
            )
    frame = pd.DataFrame(output)
    frame.to_parquet(OUTPUT_PATH, index=False)
    print(
        f"wrote {len(frame):,} unique photos for {frame['business_id'].nunique():,}/"
        f"{len(target_ids):,} recommendation/activity businesses to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
