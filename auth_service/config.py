"""Environment-backed settings for the standalone authentication service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


def _as_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _validate_origin(origin: str) -> str:
    if origin == "*":
        raise ValueError("Credentialed CORS cannot use a wildcard origin.")
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid AUTH_ALLOWED_ORIGINS entry: {origin}")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError(f"Auth CORS origins must not include a path: {origin}")
    return origin.rstrip("/")


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    environment: str = "development"
    cookie_secure: bool = False
    session_hours: int = 8
    session_cookie_name: str = "rr_auth_session"
    csrf_cookie_name: str = "rr_auth_csrf"
    after_login_url: str = "/auth/profile"
    allowed_origins: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.environment not in {"development", "test", "production"}:
            raise ValueError(f"Unsupported AUTH_ENV: {self.environment}")
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE=true is required in production.")
        normalized = tuple(
            dict.fromkeys(_validate_origin(origin) for origin in self.allowed_origins)
        )
        object.__setattr__(self, "allowed_origins", normalized)

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
            environment=os.getenv("AUTH_ENV", "development").strip().lower(),
            cookie_secure=_as_bool(os.getenv("AUTH_COOKIE_SECURE"), default=False),
            session_hours=max(1, int(os.getenv("AUTH_SESSION_HOURS", "8"))),
            after_login_url=os.getenv("AUTH_AFTER_LOGIN_URL", "/auth/profile"),
            allowed_origins=origins,
        )
