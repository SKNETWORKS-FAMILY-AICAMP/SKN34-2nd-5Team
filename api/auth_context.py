"""Authentication boundary for retention-operation writes.

The teammate-owned login/signup implementation is not present in this branch.
Until it is merged, local development uses a server-side identity configured by
environment variables. Request bodies can never choose the audit actor.

When authentication lands, replace only ``get_current_operator`` so it validates
the team's session/JWT and maps its immutable user id to ``subject``. Database
rows intentionally store that subject as text and do not duplicate the account
table or assume its primary-key type.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class OperatorIdentity:
    subject: str
    name: str
    auth_mode: str
    access_role: str


def _development_operator() -> OperatorIdentity:
    subject = os.getenv("RETENTION_DEV_OPERATOR_SUBJECT", "local-demo-operator").strip()
    name = os.getenv("RETENTION_DEV_OPERATOR_NAME", "로컬 데모 운영자").strip()
    if not subject or not name:
        raise HTTPException(status_code=503, detail="개발 운영자 설정이 필요합니다.")
    return OperatorIdentity(subject=subject, name=name, auth_mode="development", access_role="ADMIN")


def get_current_identity(request: Request) -> OperatorIdentity:
    """Resolve an authenticated identity, including read-only VIEWER accounts."""
    if os.getenv("RETENTION_ALLOW_DEV_OPERATOR", "").strip() == "1":
        return _development_operator()

    cookie = request.headers.get("cookie", "")
    if not cookie:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    auth_url = os.getenv("RETENTION_AUTH_ME_URL", "http://127.0.0.1:8100/auth/api/me")
    auth_request = UrlRequest(auth_url, headers={"Cookie": cookie, "Accept": "application/json"})
    try:
        with urlopen(auth_request, timeout=3) as response:
            user = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in {401, 403}:
            raise HTTPException(status_code=error.code, detail="유효한 로그인이 필요합니다.") from error
        raise HTTPException(status_code=503, detail="인증 서비스를 확인할 수 없습니다.") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="인증 서비스 연결에 실패했습니다.") from error

    role = user.get("access_role")
    if role not in {"ADMIN", "OPERATOR", "VIEWER"}:
        raise HTTPException(status_code=403, detail="운영 데이터 접근 권한이 없습니다.")
    return OperatorIdentity(
        subject=str(user["id"]),
        name=user.get("full_name") or user.get("username") or user.get("email") or "운영자",
        auth_mode="auth_service",
        access_role=role,
    )


def get_current_operator(request: Request) -> OperatorIdentity:
    """Resolve an identity that may mutate retention-operation data."""
    identity = get_current_identity(request)
    if identity.access_role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(status_code=403, detail="운영 데이터 변경 권한이 없습니다.")
    return identity
