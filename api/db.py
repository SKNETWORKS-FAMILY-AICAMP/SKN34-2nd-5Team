"""읽기 전용 DB 연결.

database/load/load_v04.py 의 create_engine_from_env()와 동일한 방식으로
database/.env 를 읽는다. 이 API는 SELECT만 실행하며 database/ 아래
DDL·로더는 참조만 하고 수정하지 않는다.
"""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    load_dotenv(PROJECT_ROOT / "database" / ".env")

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url, future=True, pool_pre_ping=True)

    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if os.getenv(key) is None]
    if missing:
        raise RuntimeError(
            "DB 환경변수 누락: "
            + ", ".join(missing)
            + f" (database/.env 확인, 참고: {PROJECT_ROOT / 'database' / '.env.example'})"
        )

    url = URL.create(
        drivername="mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.environ["DB_NAME"],
        query={"charset": os.getenv("DB_CHARSET", "utf8mb4")},
    )
    return create_engine(url, future=True, pool_pre_ping=True)
