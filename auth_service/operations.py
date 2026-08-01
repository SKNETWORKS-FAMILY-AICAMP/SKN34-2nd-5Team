"""Small reusable operations shared by the API, CLI, and tests."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models import (
    AccessRole,
    ApprovalAction,
    ApprovalEvent,
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
