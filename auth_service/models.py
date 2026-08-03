"""SQLAlchemy models for users, sessions, and approval audit history."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from auth_service.database import Base


def utcnow() -> datetime:
    # MySQL and SQLite both handle a naive UTC value consistently.
    return datetime.now(UTC).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


class UserStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class AccessRole(str, enum.Enum):
    VIEWER = "VIEWER"
    OPERATOR = "OPERATOR"
    ADMIN = "ADMIN"


class ApprovalAction(str, enum.Enum):
    REGISTERED = "REGISTERED"
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    REACTIVATED = "REACTIVATED"
    ROLE_CHANGED = "ROLE_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"


class User(Base):
    __tablename__ = "auth_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str | None] = mapped_column(
        String(80), unique=True, index=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    organization: Mapped[str] = mapped_column(String(120), default="")
    requested_role: Mapped[str] = mapped_column(String(80), default="운영 담당자")
    signup_reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.PENDING.value, index=True)
    access_role: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    region_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("auth_users.id"), nullable=True
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("auth_users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ApprovalEvent(Base):
    __tablename__ = "auth_approval_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("auth_users.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("auth_users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(20))
    previous_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


Index("ix_auth_users_status_created_at", User.status, User.created_at)
