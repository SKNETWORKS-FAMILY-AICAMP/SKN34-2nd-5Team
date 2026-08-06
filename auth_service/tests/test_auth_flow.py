from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from auth_service.config import Settings
from auth_service.main import create_app
from auth_service.models import AuthSession, User
from auth_service.operations import create_admin_user


@pytest.fixture()
def app_and_client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'auth-test.db').as_posix()}",
        cookie_secure=False,
        after_login_url="/auth/profile",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield app, client


def register_user(client: TestClient, email: str = "member@example.com"):
    return client.post(
        "/auth/api/register",
        json={
            "email": email,
            "password": "member-password-123",
            "full_name": "발표 사용자",
            "organization": "콘텐츠 운영팀",
            "requested_role": "운영 담당자",
            "signup_reason": "리텐션 대상자 운영",
        },
    )


def login(client: TestClient, email: str, password: str):
    return client.post(
        "/auth/api/login", json={"identifier": email, "password": password}
    )


def test_pending_user_can_be_refreshed_approved_and_logged_in(app_and_client):
    app, client = app_and_client

    registered = register_user(client)
    assert registered.status_code == 201
    assert registered.json()["user"]["status"] == "PENDING"

    pending_login = login(client, "member@example.com", "member-password-123")
    assert pending_login.status_code == 403
    assert pending_login.json()["detail"]["code"] == "approval_pending"

    with app.state.session_factory() as db:
        create_admin_user(
            db,
            username="presentation_admin",
            email="admin@example.com",
            password="admin-password-123",
            full_name="발표 관리자",
        )

    admin_login = login(client, "presentation_admin", "admin-password-123")
    assert admin_login.status_code == 200
    assert admin_login.json()["redirect_to"] == "/auth/profile"

    refreshed = client.get("/auth/api/admin/users?status=PENDING")
    assert refreshed.status_code == 200
    assert refreshed.json()["total"] == 1
    user_id = refreshed.json()["items"][0]["id"]

    csrf = client.cookies.get("rr_auth_csrf")
    approved = client.post(
        f"/auth/api/admin/users/{user_id}/approve",
        json={"note": "발표 승인", "access_role": "OPERATOR", "region_code": "IN"},
        headers={"X-CSRF-Token": csrf},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["access_role"] == "OPERATOR"
    assert approved.json()["region_code"] == "IN"

    refreshed_again = client.get("/auth/api/admin/users?status=PENDING")
    assert refreshed_again.status_code == 200
    assert refreshed_again.json()["total"] == 0

    approved_users = client.get("/auth/api/admin/users?status=APPROVED")
    assert approved_users.status_code == 200
    assert approved_users.json()["total"] == 2

    role_changed = client.patch(
        f"/auth/api/admin/users/{user_id}/role",
        json={"note": "조회 전용으로 변경", "access_role": "VIEWER"},
        headers={"X-CSRF-Token": csrf},
    )
    assert role_changed.status_code == 200
    assert role_changed.json()["access_role"] == "VIEWER"

    member_login = login(client, "member@example.com", "member-password-123")
    assert member_login.status_code == 200
    assert member_login.json()["redirect_to"] == "/auth/profile"
    me = client.get("/auth/api/me")
    assert me.status_code == 200
    assert me.json()["email"] == "member@example.com"
    assert me.json()["status"] == "APPROVED"
    assert me.json()["last_login_at"] is not None


def test_duplicate_registration_and_invalid_login_are_safe(app_and_client):
    _, client = app_and_client
    assert register_user(client).status_code == 201

    duplicate = register_user(client)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "registration_unavailable"

    invalid = login(client, "missing@example.com", "wrong-password")
    assert invalid.status_code == 401
    assert invalid.json()["detail"]["message"] == "이메일 또는 비밀번호가 올바르지 않습니다."


def test_admin_mutation_requires_csrf(app_and_client):
    app, client = app_and_client
    user_id = register_user(client).json()["user"]["id"]
    with app.state.session_factory() as db:
        create_admin_user(
            db,
            username="presentation_admin",
            email="admin@example.com",
            password="admin-password-123",
            full_name="발표 관리자",
        )
    assert login(client, "presentation_admin", "admin-password-123").status_code == 200

    without_csrf = client.post(
        f"/auth/api/admin/users/{user_id}/approve",
        json={"note": "CSRF 없이 요청", "access_role": "VIEWER"},
    )
    assert without_csrf.status_code == 403
    assert without_csrf.json()["detail"]["code"] == "csrf_failed"


def test_admin_can_create_region_and_shared_viewer_accounts(app_and_client):
    app, client = app_and_client
    with app.state.session_factory() as db:
        create_admin_user(
            db,
            username="presentation_admin",
            email="admin@example.com",
            password="admin-password-123",
            full_name="발표 관리자",
        )
    assert login(client, "presentation_admin", "admin-password-123").status_code == 200
    csrf = client.cookies.get("rr_auth_csrf")

    viewer = client.post(
        "/auth/api/admin/users",
        json={
            "username": "retention_viewer",
            "password": "Viewer!Password123",
            "full_name": "공용 조회 전용",
            "access_role": "VIEWER",
            "must_change_password": True,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert viewer.status_code == 201
    assert viewer.json()["user"]["access_role"] == "VIEWER"
    assert viewer.json()["user"]["region_code"] is None

    bulk = client.post(
        "/auth/api/admin/users/bulk-regions",
        json={"region_codes": ["AB", "AZ"], "password_length": 14},
        headers={"X-CSRF-Token": csrf},
    )
    assert bulk.status_code == 201
    assert bulk.json()["total"] == 2
    assert {item["user"]["region_code"] for item in bulk.json()["items"]} == {"AB", "AZ"}
    assert all(len(item["temporary_password"]) == 14 for item in bulk.json()["items"])


def test_shared_viewer_supports_multiple_sessions_and_cannot_become_operator_without_region(app_and_client):
    app, client = app_and_client
    with app.state.session_factory() as db:
        admin = create_admin_user(
            db,
            username="presentation_admin",
            email="admin@example.com",
            password="admin-password-123",
            full_name="발표 관리자",
        )
        from auth_service.models import AccessRole
        from auth_service.operations import create_managed_user

        viewer = create_managed_user(
            db,
            actor=admin,
            username="retention_viewer",
            password="Viewer!Password123",
            full_name="공용 조회 전용",
            access_role=AccessRole.VIEWER,
        )

    assert login(client, "retention_viewer", "Viewer!Password123").status_code == 200
    assert login(client, "retention_viewer", "Viewer!Password123").status_code == 200
    with app.state.session_factory() as db:
        session_count = db.scalar(
            select(func.count()).select_from(AuthSession).where(AuthSession.user_id == viewer.id)
        )
        assert session_count == 2
        assert db.scalar(select(User.region_code).where(User.id == viewer.id)) is None
