"""Environment-backed runtime settings for the retention API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_ORIGIN_REGEX = (
    r"^http://("
    r"localhost"
    r"|127\.0\.0\.1"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"):5173$"
)


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _validate_origin(origin: str) -> str:
    if origin == "*":
        raise ValueError("Credentialed CORS cannot use a wildcard origin.")
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid CORS origin: {origin}")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError(f"CORS origins must not include a path: {origin}")
    return origin.rstrip("/")


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    allowed_origins: tuple[str, ...] = ()
    allow_dev_operator: bool = False

    def __post_init__(self) -> None:
        if self.environment not in {"development", "test", "production"}:
            raise ValueError(f"Unsupported RETENTION_ENV: {self.environment}")
        if self.environment == "production" and self.allow_dev_operator:
            raise ValueError("RETENTION_ALLOW_DEV_OPERATOR must be disabled in production.")
        normalized = tuple(dict.fromkeys(_validate_origin(item) for item in self.allowed_origins))
        object.__setattr__(self, "allowed_origins", normalized)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / "database" / ".env", override=False)
        origins = tuple(
            item.strip()
            for item in os.getenv("RETENTION_ALLOWED_ORIGINS", "").split(",")
            if item.strip()
        )
        return cls(
            environment=os.getenv("RETENTION_ENV", "development").strip().lower(),
            allowed_origins=origins,
            allow_dev_operator=_as_bool(os.getenv("RETENTION_ALLOW_DEV_OPERATOR")),
        )
