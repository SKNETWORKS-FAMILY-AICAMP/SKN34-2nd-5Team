"""reviewer_spatial_summaries_v04.parquet를 reviewer_spatial_summary 테이블로 적재.

load_v04.py의 전체 재적재 흐름과 분리된 단독 스크립트다 — 공간 데이터는
나중에 생성됐고(pipeline/v04/build_spatial_v04.py), 다른 테이블은 이미
적재된 상태에서 이것만 추가로 얹는 경우가 일반적이라 전체 재적재를
요구하지 않는다.

사용:
    venv\\Scripts\\python.exe database\\load\\load_spatial_v04.py --confirm-database yelp_data
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

MODEL_VERSION = "v04"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_LOAD_DIR = PROJECT_ROOT / "database" / "load"
if str(DATABASE_LOAD_DIR) not in sys.path:
    sys.path.insert(0, str(DATABASE_LOAD_DIR))

from load_v04 import create_engine_from_env, database_name, sql_statements  # noqa: E402

DDL_FILES = ["011_create_spatial_tables.sql", "012_create_spatial_views.sql"]

_COLUMNS = [
    "sample_id",
    "period_type",
    "activity_year",
    "center_latitude",
    "center_longitude",
    "spatial_business_count",
    "activity_review_count",
    "median_radius_km",
    "mean_radius_km",
    "p90_radius_km",
    "max_radius_km",
    "radius_available",
    "radius_change_km",
    "radius_change_rate",
    "center_shift_km",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load v05 spatial Parquet data into the configured database."
    )
    parser.add_argument(
        "--confirm-database",
        required=True,
        help="오적재 방지 — 연결 대상 DB 이름을 그대로 입력",
    )
    parser.add_argument("--chunk-size", type=int, default=1000)
    return parser.parse_args()


def apply_spatial_schema(connection) -> None:
    ddl_dir = Path(__file__).resolve().parents[1] / "ddl"
    for filename in DDL_FILES:
        path = ddl_dir / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        for statement in sql_statements(path):
            connection.exec_driver_sql(statement)
        print(f"spatial schema applied: {path.name}")


def main() -> int:
    args = parse_args()
    engine = create_engine_from_env(PROJECT_ROOT)
    try:
        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"연결 DB({actual_database})와 확인값"
                    f"({args.confirm_database})이 다릅니다."
                )
            apply_spatial_schema(connection)

            existing = int(
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM reviewer_spatial_summary "
                    "WHERE model_version = %s",
                    (MODEL_VERSION,),
                ).scalar_one()
            )
            if existing:
                print(
                    f"reviewer_spatial_summary already has {existing:,} "
                    f"rows for {MODEL_VERSION} — skipping (delete them first "
                    "if you want to reload)."
                )
                return 0

            spatial_path = (
                PROJECT_ROOT
                / "data"
                / "processed"
                / "spatial"
                / "reviewer_spatial_summaries_v04.parquet"
            )
            if not spatial_path.is_file():
                raise FileNotFoundError(
                    f"{spatial_path} 없음 — 먼저 "
                    "v05/pipeline/build_spatial_v04.py를 실행하세요."
                )

            frame = pd.read_parquet(spatial_path)[_COLUMNS].copy()
            frame.insert(0, "model_version", MODEL_VERSION)
            # NaN -> NULL for the nullable selection-only change columns
            # (comparison rows, and selection rows with no comparable
            # baseline, leave these unset).
            frame = frame.where(pd.notna(frame), None)

            frame.to_sql(
                "reviewer_spatial_summary",
                con=connection,
                if_exists="append",
                index=False,
                chunksize=args.chunk_size,
                method="multi",
            )
            print(f"loaded: reviewer_spatial_summary ({len(frame):,} rows)")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
