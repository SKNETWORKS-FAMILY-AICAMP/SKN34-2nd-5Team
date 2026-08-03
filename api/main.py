"""React가 MySQL을 조회하고 운영 판단을 저장하는 API.

DB: MySQL yelp_data (database/.env). 분석·모델 데이터는 읽기 전용이며,
v05 운영 데이터 테이블에만 쓰기를 허용한다. database/ 아래 DDL·로더는
참조하지 않고 건드리지 않는다.

실행:
    ./.venv/Scripts/python.exe -m uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    business_photos,
    operations,
    playbooks,
    regional,
    retention_operations,
    reviewer_details,
    reviewer_radius,
    reviewers,
    trust,
    v05_derived,
)

app = FastAPI(title="Yelp Retention API (v05)")
app.include_router(business_photos.router)
app.include_router(regional.router)
app.include_router(operations.router)
app.include_router(trust.router)
app.include_router(playbooks.router)
app.include_router(retention_operations.router)
app.include_router(reviewers.router)
app.include_router(reviewer_details.router)
app.include_router(reviewer_radius.router)
app.include_router(v05_derived.router)

# Vite dev 서버. `npm run dev`는 localhost 외에 LAN 주소(예:
# http://192.168.0.18:5173)로도 열리는데, 그 주소로 접속하면 브라우저가
# 보내는 Origin이 달라져 API 호출이 CORS에서 막힌다. 개발 편의를 위해
# 사설 IP 대역까지 허용한다.
#
# 개발 전용 설정이다. 배포 시에는 이 정규식을 지우고 실제 오리진만
# allow_origins에 명시할 것.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^http://("
        r"localhost"
        r"|127\.0\.0\.1"
        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|192\.168\.\d{1,3}\.\d{1,3}"
        r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
        r"):5173$"
    ),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
