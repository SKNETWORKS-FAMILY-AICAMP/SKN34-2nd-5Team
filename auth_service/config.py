"""Environment-backed settings for the standalone authentication service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


def _as_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    cookie_secure: bool = False
    session_hours: int = 8
    session_cookie_name: str = "rr_auth_session"
    csrf_cookie_name: str = "rr_auth_csrf"
    after_login_url: str = "/auth/profile"
    allowed_origins: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(BASE_DIR / ".env", override=False)
        default_db = f"sqlite:///{(BASE_DIR / 'auth_service.db').as_posix()}"
        origins = tuple(
            origin.strip()
            for origin in os.getenv("AUTH_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )
        return cls(
            database_url=os.getenv("AUTH_DATABASE_URL", default_db),
            cookie_secure=_as_bool(os.getenv("AUTH_COOKIE_SECURE"), default=False),
            session_hours=max(1, int(os.getenv("AUTH_SESSION_HOURS", "8"))),
            after_login_url=os.getenv("AUTH_AFTER_LOGIN_URL", "/auth/profile"),
            allowed_origins=origins,
        )
