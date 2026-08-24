from __future__ import annotations

import json
from urllib.error import URLError

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

from api import auth_context
from api.auth_context import OperatorIdentity, get_current_identity
from api.config import Settings
from api.main import app, create_app
from api.routers import retention_operations
from api.services.retention_operation_service import regions_for_identity


class _AuthResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _request_with_cookie() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/retention/decisions",
            "headers": [(b"cookie", b"rr_auth_session=test-session")],
        }
    )


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_retention_reads_require_a_login():
    with TestClient(app) as client:
        for path in (
            "/api/retention/decisions",
            "/api/retention/target-lists",
            "/api/retention/action-plans",
        ):
            response = client.get(path)
            assert response.status_code == 401
            assert response.json()["detail"] == "로그인이 필요합니다."


def test_auth_service_failure_is_reported_as_503(monkeypatch):
    def fail_auth(*args, **kwargs):
        raise URLError("auth unavailable")

    monkeypatch.setattr(auth_context, "urlopen", fail_auth)
    with TestClient(app) as client:
        response = client.get(
            "/api/retention/decisions",
            headers={"Cookie": "rr_auth_session=test-session"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "인증 서비스 연결에 실패했습니다."


def test_production_cors_allows_only_configured_origin():
    production_app = create_app(
        Settings(
            environment="production",
            allowed_origins=("https://retention.example.com",),
        )
    )
    with TestClient(production_app) as client:
        allowed = client.options(
            "/api/retention/decisions",
            headers={
                "Origin": "https://retention.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        rejected = client.options(
            "/api/retention/decisions",
            headers={
                "Origin": "https://untrusted.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://retention.example.com"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert "access-control-allow-origin" not in rejected.headers


def test_credentialed_cors_rejects_wildcard_origin():
    with pytest.raises(ValueError, match="wildcard"):
        Settings(environment="production", allowed_origins=("*",))


def test_production_rejects_development_identity():
    with pytest.raises(ValueError, match="RETENTION_ALLOW_DEV_OPERATOR"):
        Settings(environment="production", allow_dev_operator=True)


def test_database_failure_returns_sanitized_503(monkeypatch):
    viewer = OperatorIdentity(
        subject="viewer-1",
        name="조회 사용자",
        auth_mode="test",
        access_role="VIEWER",
    )
    app.dependency_overrides[get_current_identity] = lambda: viewer
    monkeypatch.setattr(retention_operations, "get_engine", lambda: object())

    def database_down(*args, **kwargs):
        raise OperationalError(
            "SELECT secret FROM retention_decisions",
            {"password": "must-not-leak"},
            ConnectionError("database unavailable"),
        )

    monkeypatch.setattr(retention_operations, "list_decisions", database_down)
    with TestClient(app) as client:
        response = client.get("/api/retention/decisions")

    assert response.status_code == 503
    assert response.json()["detail"] == "운영 데이터베이스에 연결할 수 없습니다"
    assert "secret" not in response.text
    assert "password" not in response.text


def test_operator_identity_uses_auth_service_region(monkeypatch):
    monkeypatch.delenv("RETENTION_ALLOW_DEV_OPERATOR", raising=False)
    monkeypatch.setattr(
        auth_context,
        "urlopen",
        lambda *args, **kwargs: _AuthResponse(
            {
                "id": "operator-1",
                "full_name": "NV 운영자",
                "access_role": "OPERATOR",
                "region_code": "nv",
            }
        ),
    )

    identity = get_current_identity(_request_with_cookie())

    assert identity.subject == "operator-1"
    assert identity.access_role == "OPERATOR"
    assert identity.region_code == "NV"
    assert regions_for_identity(object(), identity) == ["NV"]


def test_operator_without_region_is_rejected(monkeypatch):
    monkeypatch.delenv("RETENTION_ALLOW_DEV_OPERATOR", raising=False)
    monkeypatch.setattr(
        auth_context,
        "urlopen",
        lambda *args, **kwargs: _AuthResponse(
            {
                "id": "operator-1",
                "full_name": "미배정 운영자",
                "access_role": "OPERATOR",
                "region_code": None,
            }
        ),
    )

    with pytest.raises(HTTPException) as error:
        get_current_identity(_request_with_cookie())

    assert error.value.status_code == 403
    assert error.value.detail == "운영자 담당 권역이 설정되지 않았습니다."


def test_operator_reads_only_assigned_region_decisions(monkeypatch):
    operator = OperatorIdentity(
        subject="operator-nv",
        name="NV 운영자",
        auth_mode="test",
        access_role="OPERATOR",
        region_code="NV",
    )
    app.dependency_overrides[get_current_identity] = lambda: operator
    monkeypatch.setattr(retention_operations, "get_engine", lambda: object())
    monkeypatch.setattr(
        retention_operations,
        "reviewer_ids_for_regions",
        lambda engine, regions: {"reviewer-nv"},
    )
    monkeypatch.setattr(
        retention_operations,
        "list_decisions",
        lambda engine, model_version: [
            {"reviewerUserId": "reviewer-nv", "decision": "변화 지켜보기"},
            {"reviewerUserId": "reviewer-nj", "decision": "이번엔 제외"},
        ],
    )

    with TestClient(app) as client:
        response = client.get("/api/retention/decisions?model_version=v05_05_dl")

    assert response.status_code == 200
    assert [item["reviewerUserId"] for item in response.json()["items"]] == [
        "reviewer-nv"
    ]


def test_operator_cannot_save_another_region_reviewer(monkeypatch):
    operator = OperatorIdentity(
        subject="operator-nv",
        name="NV 운영자",
        auth_mode="test",
        access_role="OPERATOR",
        region_code="NV",
    )
    app.dependency_overrides[get_current_identity] = lambda: operator
    monkeypatch.setattr(retention_operations, "get_engine", lambda: object())
    monkeypatch.setattr(
        retention_operations,
        "reviewer_ids_for_regions",
        lambda engine, regions: {"reviewer-nv"},
    )
    monkeypatch.setattr(
        retention_operations,
        "save_decision",
        lambda *args, **kwargs: pytest.fail("out-of-region save reached the service"),
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/retention/decisions/reviewer-nj",
            json={
                "modelVersion": "v05_05_dl",
                "sampleId": "sample-nj",
                "decision": "변화 지켜보기",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "배정된 권역의 핵심 리뷰어만 처리할 수 있습니다"


def test_viewer_cannot_mutate_retention_data(monkeypatch):
    viewer = OperatorIdentity(
        subject="viewer-1",
        name="조회 사용자",
        auth_mode="test",
        access_role="VIEWER",
    )
    app.dependency_overrides[get_current_identity] = lambda: viewer
    monkeypatch.setattr(
        retention_operations,
        "save_decision",
        lambda *args, **kwargs: pytest.fail("viewer save reached the service"),
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/retention/decisions/reviewer-nv",
            json={
                "modelVersion": "v05_05_dl",
                "sampleId": "sample-nv",
                "decision": "변화 지켜보기",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "운영 데이터 변경 권한이 없습니다."


def test_operator_cannot_save_another_region_plan(monkeypatch):
    operator = OperatorIdentity(
        subject="operator-nv",
        name="NV 운영자",
        auth_mode="test",
        access_role="OPERATOR",
        region_code="NV",
    )
    app.dependency_overrides[get_current_identity] = lambda: operator
    monkeypatch.setattr(retention_operations, "get_engine", lambda: object())
    monkeypatch.setattr(
        retention_operations,
        "save_action_plan",
        lambda *args, **kwargs: pytest.fail("out-of-region plan reached the service"),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/retention/action-plans",
            json={
                "planType": "regional",
                "modelVersion": "v05_05_dl",
                "regionCode": "NJ",
                "targetScope": "region",
                "actionType": "지역 캠페인 검토",
                "status": "draft",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "배정된 권역만 처리할 수 있습니다"
