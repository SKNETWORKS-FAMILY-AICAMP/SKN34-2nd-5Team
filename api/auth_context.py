"""Authentication boundary for the reviewer-retention API.

Production requests are resolved through ``auth_service``'s server-side session.
Request bodies can never choose the audit actor, role, or assigned region.  The
development identity is an explicit opt-in for local work only.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request


@dataclass(frozen=True)
class OperatorIdentity:
    subject: str
    name: str
    auth_mode: str
    access_role: str
    region_code: str | None = None


def _development_operator() -> OperatorIdentity:
    subject = os.getenv("RETENTION_DEV_OPERATOR_SUBJECT", "local-demo-operator").strip()
    name = os.getenv("RETENTION_DEV_OPERATOR_NAME", "로컬 데모 운영자").strip()
    if not subject or not name:
        raise HTTPException(status_code=503, detail="개발 운영자 설정이 필요합니다.")
    return OperatorIdentity(
        subject=subject,
        name=name,
        auth_mode="development",
        access_role="ADMIN",
        region_code=None,
    )


def get_current_identity(request: Request) -> OperatorIdentity:
    """Resolve an authenticated identity, including read-only VIEWER accounts."""
    application = request.scope.get("app")
    settings = getattr(getattr(application, "state", None), "settings", None)
    allow_dev_operator = getattr(settings, "allow_dev_operator", None)
    if allow_dev_operator is None:
        allow_dev_operator = os.getenv("RETENTION_ALLOW_DEV_OPERATOR", "").strip() == "1"
    if allow_dev_operator:
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

    subject = str(user.get("id") or "").strip()
    role = user.get("access_role")
    if role not in {"ADMIN", "OPERATOR", "VIEWER"}:
        raise HTTPException(status_code=403, detail="운영 데이터 접근 권한이 없습니다.")
    if not subject:
        raise HTTPException(status_code=503, detail="인증 사용자 식별자가 없습니다.")
    raw_region = user.get("region_code")
    region_code = str(raw_region).strip().upper() if raw_region else None
    if role == "OPERATOR" and not region_code:
        raise HTTPException(status_code=403, detail="운영자 담당 권역이 설정되지 않았습니다.")
    return OperatorIdentity(
        subject=subject,
        name=user.get("full_name") or user.get("username") or user.get("email") or "운영자",
        auth_mode="auth_service",
        access_role=role,
        region_code=region_code,
    )


def get_current_operator(
    identity: OperatorIdentity = Depends(get_current_identity),
) -> OperatorIdentity:
    """Resolve an identity that may mutate retention-operation data."""
    if identity.access_role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(status_code=403, detail="운영 데이터 변경 권한이 없습니다.")
    return identity
