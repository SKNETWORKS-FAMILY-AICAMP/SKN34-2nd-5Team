"""Standalone FastAPI membership service; it does not import the analysis API or React app."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, FastAPI, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from auth_service.config import BASE_DIR, Settings
from auth_service.database import build_engine, build_session_factory, initialize_database
from auth_service.dependencies import (
    AdminContext,
    AdminCsrfContext,
    Authenticated,
    CsrfProtected,
    DatabaseSession,
    api_error,
)
from auth_service.models import (
    AccessRole,
    ApprovalAction,
    ApprovalEvent,
    AuthSession,
    User,
    UserStatus,
    utcnow,
)
from auth_service.operations import (
    apply_password_reset,
    create_managed_user,
    find_user_by_email,
    find_user_by_identifier,
    generate_temporary_password,
    normalize_email,
)
from auth_service.schemas import (
    AdminBulkRegionUsersRequest,
    AdminUserCreateRequest,
    AdminUserStatusRequest,
    ApprovalRequest,
    BulkUserCreateResponse,
    CreatedCredential,
    DecisionRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    PasswordResetRequest,
    RegisterRequest,
    RegistrationResponse,
    RoleUpdateRequest,
    UserListResponse,
    UserResponse,
)
from auth_service.security import (
    hash_password,
    new_token,
    perform_dummy_password_check,
    token_digest,
    verify_password,
)


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _set_auth_cookies(
    response: Response, request: Request, *, session_token: str, csrf_token: str
) -> None:
    settings: Settings = request.app.state.settings
    max_age = settings.session_hours * 60 * 60
    common = {
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
        "max_age": max_age,
    }
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        httponly=True,
        **common,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        **common,
    )


def _clear_auth_cookies(response: Response, request: Request) -> None:
    settings: Settings = request.app.state.settings
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


def _user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def build_api_router() -> APIRouter:
    router = APIRouter(prefix="/auth/api", tags=["authentication"])

    @router.post(
        "/register",
        response_model=RegistrationResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def register(payload: RegisterRequest, db: DatabaseSession) -> RegistrationResponse:
        email = normalize_email(str(payload.email))
        if find_user_by_email(db, email) is not None:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "registration_unavailable",
                "해당 정보로 가입 요청을 처리할 수 없습니다.",
            )

        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            organization=payload.organization,
            requested_role=payload.requested_role,
            signup_reason=payload.signup_reason,
            status=UserStatus.PENDING.value,
        )
        db.add(user)
        try:
            db.flush()
            db.add(
                ApprovalEvent(
                    user_id=user.id,
                    action=ApprovalAction.REGISTERED.value,
                    note="회원가입 신청",
                )
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise api_error(
                status.HTTP_409_CONFLICT,
                "registration_unavailable",
                "해당 정보로 가입 요청을 처리할 수 없습니다.",
            )
        db.refresh(user)
        return RegistrationResponse(
            message="가입 신청이 접수되었습니다. 관리자 승인을 기다려 주세요.",
            user=_user_response(user),
        )

    @router.post("/login", response_model=LoginResponse)
    def login(payload: LoginRequest, request: Request, response: Response, db: DatabaseSession) -> LoginResponse:
        user = find_user_by_identifier(db, payload.identifier)
        if user is None:
            perform_dummy_password_check(payload.password)
            raise api_error(
                status.HTTP_401_UNAUTHORIZED,
                "invalid_credentials",
                "이메일 또는 비밀번호가 올바르지 않습니다.",
            )
        if not verify_password(user.password_hash, payload.password):
            raise api_error(
                status.HTTP_401_UNAUTHORIZED,
                "invalid_credentials",
                "이메일 또는 비밀번호가 올바르지 않습니다.",
            )
        if user.status == UserStatus.PENDING.value:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "approval_pending",
                "관리자 승인 대기 중입니다.",
            )
        if user.status != UserStatus.APPROVED.value:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "account_unavailable",
                "현재 사용할 수 없는 계정입니다.",
            )

        settings: Settings = request.app.state.settings
        session_token = new_token()
        csrf_token = new_token()
        auth_session = AuthSession(
            user_id=user.id,
            token_hash=token_digest(session_token),
            csrf_hash=token_digest(csrf_token),
            expires_at=utcnow() + timedelta(hours=settings.session_hours),
        )
        user.last_login_at = utcnow()
        db.add(auth_session)
        db.commit()
        _set_auth_cookies(
            response,
            request,
            session_token=session_token,
            csrf_token=csrf_token,
        )
        redirect_to = "/auth/admin" if user.is_admin else settings.after_login_url
        return LoginResponse(
            message="로그인되었습니다.",
            user=_user_response(user),
            redirect_to=redirect_to,
        )

    @router.post("/logout", response_model=MessageResponse)
    def logout(request: Request, response: Response, auth: CsrfProtected, db: DatabaseSession) -> MessageResponse:
        auth.session.revoked_at = utcnow()
        db.commit()
        _clear_auth_cookies(response, request)
        return MessageResponse(message="로그아웃되었습니다.")

    @router.get("/me", response_model=UserResponse)
    def me(auth: Authenticated) -> UserResponse:
        return _user_response(auth.user)

    @router.get("/verify", status_code=status.HTTP_204_NO_CONTENT)
    def verify(auth: Authenticated) -> Response:
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers={
                "X-Auth-User-Id": auth.user.id,
                "X-Auth-User-Email": auth.user.email,
                "X-Auth-Is-Admin": str(auth.user.is_admin).lower(),
                "X-Auth-Role": auth.user.access_role or "",
            },
        )

    @router.get("/admin/users", response_model=UserListResponse)
    def list_users(
        admin: AdminContext,
        db: DatabaseSession,
        user_status: UserStatus = Query(UserStatus.PENDING, alias="status"),
    ) -> UserListResponse:
        del admin
        filters = (User.status == user_status.value,)
        items = db.scalars(
            select(User).where(*filters).order_by(User.created_at.desc())
        ).all()
        total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
        return UserListResponse(items=[_user_response(user) for user in items], total=total)

    @router.post(
        "/admin/users",
        response_model=CreatedCredential,
        status_code=status.HTTP_201_CREATED,
    )
    def create_user(
        payload: AdminUserCreateRequest,
        admin: AdminCsrfContext,
        db: DatabaseSession,
    ) -> CreatedCredential:
        try:
            user = create_managed_user(
                db,
                actor=admin.user,
                username=payload.username,
                email=str(payload.email) if payload.email else None,
                password=payload.password,
                full_name=payload.full_name,
                access_role=AccessRole(payload.access_role),
                region_code=payload.region_code,
                must_change_password=payload.must_change_password,
            )
        except ValueError as error:
            db.rollback()
            raise api_error(
                status.HTTP_409_CONFLICT,
                "account_creation_failed",
                str(error),
            ) from error
        return CreatedCredential(user=_user_response(user), temporary_password=payload.password)

    @router.post(
        "/admin/users/bulk-regions",
        response_model=BulkUserCreateResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_region_users(
        payload: AdminBulkRegionUsersRequest,
        admin: AdminCsrfContext,
        db: DatabaseSession,
    ) -> BulkUserCreateResponse:
        created: list[tuple[User, str]] = []
        try:
            for region_code in payload.region_codes:
                username = f"region_{region_code.lower()}_ops"
                temporary_password = generate_temporary_password(payload.password_length)
                user = create_managed_user(
                    db,
                    actor=admin.user,
                    username=username,
                    password=temporary_password,
                    full_name=f"{region_code} 권역 운영자",
                    access_role=AccessRole.OPERATOR,
                    region_code=region_code,
                    must_change_password=payload.must_change_password,
                    commit=False,
                )
                created.append((user, temporary_password))
            db.commit()
            for user, _ in created:
                db.refresh(user)
        except ValueError as error:
            db.rollback()
            raise api_error(
                status.HTTP_409_CONFLICT,
                "bulk_account_creation_failed",
                str(error),
            ) from error
        return BulkUserCreateResponse(
            items=[
                CreatedCredential(user=_user_response(user), temporary_password=password)
                for user, password in created
            ],
            total=len(created),
        )

    def decide_user(
        *,
        user_id: str,
        payload: DecisionRequest,
        admin: AdminCsrfContext,
        db: DatabaseSession,
        target_status: UserStatus,
        action: ApprovalAction,
        access_role: AccessRole | None = None,
        region_code: str | None = None,
    ) -> UserResponse:
        user = db.get(User, user_id)
        if user is None or user.is_admin:
            raise api_error(status.HTTP_404_NOT_FOUND, "user_not_found", "가입 신청을 찾을 수 없습니다.")
        if user.status != UserStatus.PENDING.value:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "already_decided",
                "이미 처리된 가입 신청입니다. 목록을 새로고침해 주세요.",
            )

        user.status = target_status.value
        if target_status == UserStatus.APPROVED:
            user.approved_at = utcnow()
            user.approved_by_id = admin.user.id
            user.access_role = (access_role or AccessRole.VIEWER).value
            user.region_code = region_code if user.access_role == AccessRole.OPERATOR.value else None
        db.add(
            ApprovalEvent(
                user_id=user.id,
                actor_user_id=admin.user.id,
                action=action.value,
                previous_role=None,
                new_role=user.access_role if target_status == UserStatus.APPROVED else None,
                note=payload.note,
            )
        )
        db.commit()
        db.refresh(user)
        return _user_response(user)

    @router.post("/admin/users/{user_id}/approve", response_model=UserResponse)
    def approve_user(
        user_id: str,
        payload: ApprovalRequest,
        admin: AdminCsrfContext,
        db: DatabaseSession,
    ) -> UserResponse:
        return decide_user(
            user_id=user_id,
            payload=payload,
            admin=admin,
            db=db,
            target_status=UserStatus.APPROVED,
            action=ApprovalAction.APPROVED,
            access_role=AccessRole(payload.access_role),
            region_code=payload.region_code,
        )

    @router.post("/admin/users/{user_id}/reject", response_model=UserResponse)
    def reject_user(
        user_id: str,
        payload: DecisionRequest,
        admin: AdminCsrfContext,
        db: DatabaseSession,
    ) -> UserResponse:
        return decide_user(
            user_id=user_id,
            payload=payload,
            admin=admin,
            db=db,
            target_status=UserStatus.REJECTED,
            action=ApprovalAction.REJECTED,
        )

    @router.patch("/admin/users/{user_id}/role", response_model=UserResponse)
    def update_user_role(
        user_id: str,
        payload: RoleUpdateRequest,
        admin: AdminCsrfContext,
        db: DatabaseSession,
    ) -> UserResponse:
        user = db.get(User, user_id)
        if user is None or user.is_admin:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                "user_not_found",
                "권한을 변경할 회원을 찾을 수 없습니다.",
            )
        if user.status != UserStatus.APPROVED.value:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "user_not_approved",
                "승인 완료된 회원의 권한만 변경할 수 있습니다.",
            )

        previous_role = user.access_role
        previous_region = user.region_code
        if payload.access_role == AccessRole.OPERATOR.value and not payload.region_code:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "region_required",
                "운영자 계정에는 담당 권역이 필요합니다.",
            )
        if previous_role == payload.access_role and previous_region == payload.region_code:
            return _user_response(user)

        user.access_role = payload.access_role
        user.region_code = payload.region_code if payload.access_role == AccessRole.OPERATOR.value else None
        db.add(
            ApprovalEvent(
                user_id=user.id,
                actor_user_id=admin.user.id,
                action=ApprovalAction.ROLE_CHANGED.value,
                previous_role=previous_role,
                new_role=payload.access_role,
                note=(
                    f"{payload.note} · 담당 권역 {previous_region or '전체'} → "
                    f"{user.region_code or '전체'}"
                ).strip(" ·"),
            )
        )
        db.commit()
        db.refresh(user)
        return _user_response(user)

    @router.patch("/admin/users/{user_id}/status", response_model=UserResponse)
    def update_user_status(
        user_id: str,
        payload: AdminUserStatusRequest,
        admin: AdminCsrfContext,
        db: DatabaseSession,
    ) -> UserResponse:
        user = db.get(User, user_id)
        if user is None or user.is_admin:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                "user_not_found",
                "상태를 변경할 사용자를 찾을 수 없습니다.",
            )
        target_status = UserStatus.APPROVED if payload.active else UserStatus.SUSPENDED
        if user.status == target_status.value:
            return _user_response(user)
        previous_status = user.status
        user.status = target_status.value
        if not payload.active:
            for session_row in db.scalars(
                select(AuthSession).where(
                    AuthSession.user_id == user.id,
                    AuthSession.revoked_at.is_(None),
                )
            ):
                session_row.revoked_at = utcnow()
        db.add(
            ApprovalEvent(
                user_id=user.id,
                actor_user_id=admin.user.id,
                action=(
                    ApprovalAction.REACTIVATED.value
                    if payload.active
                    else ApprovalAction.SUSPENDED.value
                ),
                previous_role=user.access_role,
                new_role=user.access_role,
                note=payload.note or f"계정 상태 {previous_status} → {target_status.value}",
            )
        )
        db.commit()
        db.refresh(user)
        return _user_response(user)

    @router.patch("/admin/users/{user_id}/password", response_model=UserResponse)
    def reset_user_password(
        user_id: str,
        payload: PasswordResetRequest,
        admin: AdminCsrfContext,
        db: DatabaseSession,
    ) -> UserResponse:
        user = db.get(User, user_id)
        if user is None or user.is_admin:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                "user_not_found",
                "비밀번호를 재설정할 사용자를 찾을 수 없습니다.",
            )
        apply_password_reset(
            db, user=user, new_password=payload.new_password, must_change_password=True
        )
        db.add(
            ApprovalEvent(
                user_id=user.id,
                actor_user_id=admin.user.id,
                action=ApprovalAction.PASSWORD_RESET.value,
                previous_role=user.access_role,
                new_role=user.access_role,
                note=payload.note or "설정 화면에서 비밀번호 재설정",
            )
        )
        db.commit()
        db.refresh(user)
        return _user_response(user)

    return router


def _page(name: str, title: str):
    def render(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request=request, name=name, context={"title": title})

    return render


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    engine = build_engine(resolved_settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="Reviewer Retention Auth Service",
        version="0.1.0",
        docs_url="/auth/docs",
        redoc_url=None,
        openapi_url="/auth/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    if resolved_settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.allowed_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )

    app.mount("/auth/static", StaticFiles(directory=Path(BASE_DIR / "static")), name="auth-static")
    app.include_router(build_api_router())

    @app.get("/auth", include_in_schema=False)
    def auth_home() -> RedirectResponse:
        return RedirectResponse("/auth/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    app.add_api_route("/auth/signup", _page("signup.html", "회원가입"), methods=["GET"], include_in_schema=False)
    app.add_api_route("/auth/login", _page("login.html", "로그인"), methods=["GET"], include_in_schema=False)
    app.add_api_route("/auth/pending", _page("pending.html", "승인 대기"), methods=["GET"], include_in_schema=False)
    app.add_api_route("/auth/profile", _page("profile.html", "회원 정보"), methods=["GET"], include_in_schema=False)
    app.add_api_route("/auth/admin", _page("admin.html", "가입 승인 관리"), methods=["GET"], include_in_schema=False)
    return app


app = create_app()
