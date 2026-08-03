"""Password and opaque session-token helpers."""

from __future__ import annotations

import hashlib
import os
import secrets
import threading

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


_password_hasher = PasswordHasher()
_dummy_hash = _password_hasher.hash("not-a-real-user-password")


def _password_verify_concurrency() -> int:
    raw_value = os.getenv("AUTH_PASSWORD_VERIFY_CONCURRENCY", "2")
    try:
        return max(1, int(raw_value))
    except ValueError:
        return 2


# Argon2 intentionally consumes substantial memory. A small semaphore keeps a
# burst of shared-account logins from running dozens of verifications at once
# on a memory-constrained demo server. Requests wait here; users are not capped.
_password_verify_slots = threading.BoundedSemaphore(_password_verify_concurrency())


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    with _password_verify_slots:
        try:
            return _password_hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False


def perform_dummy_password_check(password: str) -> None:
    verify_password(_dummy_hash, password)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
