"""FastAPI dependencies for database sessions and authenticated users."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Annotated, Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models import AuthSession, User, UserStatus, utcnow
from auth_service.security import token_digest


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as db:
        yield db


DatabaseSession = Annotated[Session, Depends(get_db)]


@dataclass(slots=True)
class AuthContext:
    user: User
    session: AuthSession


def get_auth_context(request: Request, db: DatabaseSession) -> AuthContext:
    settings = request.app.state.settings
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "not_authenticated", "로그인이 필요합니다.")

    row = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(AuthSession.token_hash == token_digest(raw_token))
    ).one_or_none()
    if row is None:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "invalid_session", "로그인이 필요합니다.")

    auth_session, user = row
    if auth_session.revoked_at is not None or auth_session.expires_at <= utcnow():
        raise api_error(status.HTTP_401_UNAUTHORIZED, "expired_session", "세션이 만료되었습니다.")
    if user.status != UserStatus.APPROVED.value:
        raise api_error(status.HTTP_403_FORBIDDEN, "account_unavailable", "사용할 수 없는 계정입니다.")
    return AuthContext(user=user, session=auth_session)


Authenticated = Annotated[AuthContext, Depends(get_auth_context)]


def require_admin(auth: Authenticated) -> AuthContext:
    if not auth.user.is_admin:
        raise api_error(status.HTTP_403_FORBIDDEN, "admin_required", "관리자 권한이 필요합니다.")
    return auth


AdminContext = Annotated[AuthContext, Depends(require_admin)]


def require_csrf(request: Request, auth: Authenticated) -> AuthContext:
    settings = request.app.state.settings
    header_token = request.headers.get("x-csrf-token", "")
    cookie_token = request.cookies.get(settings.csrf_cookie_name, "")
    valid = (
        bool(header_token)
        and bool(cookie_token)
        and secrets.compare_digest(header_token, cookie_token)
        and secrets.compare_digest(token_digest(header_token), auth.session.csrf_hash)
    )
    if not valid:
        raise api_error(status.HTTP_403_FORBIDDEN, "csrf_failed", "요청을 확인할 수 없습니다.")
    return auth


CsrfProtected = Annotated[AuthContext, Depends(require_csrf)]


def require_admin_csrf(auth: CsrfProtected) -> AuthContext:
    if not auth.user.is_admin:
        raise api_error(status.HTTP_403_FORBIDDEN, "admin_required", "관리자 권한이 필요합니다.")
    return auth


AdminCsrfContext = Annotated[AuthContext, Depends(require_admin_csrf)]
