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

import os
from dataclasses import dataclass

from fastapi import HTTPException


@dataclass(frozen=True)
class OperatorIdentity:
    subject: str
    name: str
    auth_mode: str


def get_current_operator() -> OperatorIdentity:
    subject = os.getenv("RETENTION_DEV_OPERATOR_SUBJECT", "local-demo-operator").strip()
    name = os.getenv("RETENTION_DEV_OPERATOR_NAME", "로컬 데모 운영자").strip()
    if not subject or not name:
        raise HTTPException(
            status_code=503,
            detail="로그인 사용자 연동 또는 개발 운영자 설정이 필요합니다",
        )
    return OperatorIdentity(subject=subject, name=name, auth_mode="development")
