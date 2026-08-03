"""Small reusable operations shared by the API, CLI, and tests."""

from __future__ import annotations

import re
import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models import (
    AccessRole,
    ApprovalAction,
    ApprovalEvent,
    AuthSession,
    User,
    UserStatus,
    utcnow,
)
from auth_service.security import hash_password


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,79}", normalized):
        raise ValueError("아이디는 영문자로 시작하는 3~80자의 영문·숫자·._- 조합이어야 합니다.")
    return normalized


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def find_user_by_identifier(db: Session, identifier: str) -> User | None:
    normalized = identifier.strip().lower()
    return db.scalar(
        select(User).where((User.email == normalized) | (User.username == normalized))
    )


def create_admin_user(
    db: Session,
    *,
    password: str,
    full_name: str,
    username: str | None = None,
    email: str | None = None,
) -> User:
    if username is None and email is None:
        raise ValueError("관리자 아이디 또는 이메일이 필요합니다.")

    normalized_username = normalize_username(username or str(email).split("@", 1)[0])
    normalized_email = normalize_email(email or f"{normalized_username}@example.com")
    if find_user_by_identifier(db, normalized_username) is not None:
        raise ValueError("이미 등록된 관리자 아이디입니다.")
    if find_user_by_email(db, normalized_email) is not None:
        raise ValueError("이미 등록된 이메일입니다.")

    now = utcnow()
    user = User(
        username=normalized_username,
        email=normalized_email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        organization="서비스 운영팀",
        requested_role="관리자",
        signup_reason="서버에서 생성된 관리자 계정",
        status=UserStatus.APPROVED.value,
        access_role=AccessRole.ADMIN.value,
        is_admin=True,
        approved_at=now,
    )
    db.add(user)
    db.flush()
    db.add(
        ApprovalEvent(
            user_id=user.id,
            actor_user_id=user.id,
            action=ApprovalAction.APPROVED.value,
            new_role=AccessRole.ADMIN.value,
            note="관리자 계정 생성",
        )
    )
    db.commit()
    db.refresh(user)
    return user


def apply_password_reset(
    db: Session,
    *,
    user: User,
    new_password: str,
    must_change_password: bool = False,
) -> None:
    """Set a new password hash and revoke the user's active sessions.

    Doesn't add the ApprovalEvent audit row or commit — callers (CLI, API)
    attach their own event note first, mirroring update_user_role/
    update_user_status in main.py.
    """
    user.password_hash = hash_password(new_password)
    user.must_change_password = must_change_password
    for session_row in db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
    ):
        session_row.revoked_at = utcnow()


def generate_temporary_password(length: int = 14) -> str:
    """Generate a one-time password containing every required character class."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    required.extend(secrets.choice(alphabet) for _ in range(max(0, length - 4)))
    secrets.SystemRandom().shuffle(required)
    return "".join(required)


def create_managed_user(
    db: Session,
    *,
    actor: User,
    username: str,
    password: str,
    full_name: str,
    access_role: AccessRole,
    email: str | None = None,
    region_code: str | None = None,
    must_change_password: bool = True,
    commit: bool = True,
) -> User:
    normalized_username = normalize_username(username)
    normalized_email = normalize_email(email or f"{normalized_username}@example.com")
    if find_user_by_identifier(db, normalized_username) is not None:
        raise ValueError(f"이미 사용 중인 아이디입니다: {normalized_username}")
    if find_user_by_email(db, normalized_email) is not None:
        raise ValueError(f"이미 사용 중인 이메일입니다: {normalized_email}")
    normalized_region = region_code.strip().upper() if region_code else None
    if access_role == AccessRole.OPERATOR and not normalized_region:
        raise ValueError("운영자 계정에는 담당 권역이 필요합니다.")

    now = utcnow()
    user = User(
        username=normalized_username,
        email=normalized_email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        organization="Reviewer Retention Ops",
        requested_role="관리자 생성 계정",
        signup_reason="설정 화면에서 관리자가 직접 생성",
        status=UserStatus.APPROVED.value,
        access_role=access_role.value,
        region_code=normalized_region,
        must_change_password=must_change_password,
        is_admin=False,
        approved_at=now,
        approved_by_id=actor.id,
    )
    db.add(user)
    db.flush()
    db.add(
        ApprovalEvent(
            user_id=user.id,
            actor_user_id=actor.id,
            action=ApprovalAction.ACCOUNT_CREATED.value,
            new_role=access_role.value,
            note=f"관리자 직접 생성 · 담당 권역 {normalized_region or '전체'}",
        )
    )
    if commit:
        db.commit()
        db.refresh(user)
    return user
