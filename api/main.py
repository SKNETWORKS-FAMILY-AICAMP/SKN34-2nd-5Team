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

from api.config import DEVELOPMENT_ORIGIN_REGEX, Settings
from api.routers import (
    business_photos,
    operations,
    playbooks,
    regional,
    retention_operations,
    reviewer_details,
    reviewer_radius,
    reviewers,
    sponsorships,
    trust,
    v05_derived,
)

def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings.from_env()
    application = FastAPI(title="Yelp Retention API (v05)")
    application.state.settings = resolved

    application.include_router(business_photos.router)
    application.include_router(regional.router)
    application.include_router(operations.router)
    application.include_router(trust.router)
    application.include_router(playbooks.router)
    application.include_router(retention_operations.router)
    application.include_router(reviewers.router)
    application.include_router(reviewer_details.router)
    application.include_router(reviewer_radius.router)
    application.include_router(v05_derived.router)
    application.include_router(sponsorships.router)

    cors_options: dict = {}
    if resolved.allowed_origins:
        cors_options["allow_origins"] = list(resolved.allowed_origins)
    elif resolved.environment == "development":
        cors_options["allow_origin_regex"] = DEVELOPMENT_ORIGIN_REGEX
    if cors_options:
        application.add_middleware(
            CORSMiddleware,
            **cors_options,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Accept", "Content-Type"],
            allow_credentials=True,
        )

    @application.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "environment": resolved.environment,
            "developmentOperator": resolved.allow_dev_operator,
        }

    return application


app = create_app()
