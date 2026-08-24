"""Rollback-only integration validation for retention decision persistence.

The script uses the configured MySQL database and exercises the production
service functions inside one outer transaction.  It always rolls the
transaction back, so the selected reviewer, history, and review alerts are not
changed after the validation finishes.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.auth_context import OperatorIdentity
from api.db import get_engine
from api.services.retention_operation_service import (
    list_decisions,
    list_history,
    save_decision,
)


class _RollbackEngine:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


def main() -> None:
    engine = get_engine()
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            sample = connection.execute(
                text(
                    """
                    SELECT sample.user_id, sample.sample_id, sample.model_version
                    FROM cohort_samples AS sample
                    LEFT JOIN retention_decisions AS decision_row
                      ON decision_row.reviewer_user_id = sample.user_id
                    WHERE sample.model_version = 'v05_05_dl'
                      AND decision_row.reviewer_user_id IS NULL
                    ORDER BY sample.sample_id
                    LIMIT 1
                    """
                )
            ).mappings().first()
            if sample is None:
                raise RuntimeError("롤백 검증에 사용할 미검토 리뷰어가 없습니다.")

            rollback_engine = _RollbackEngine(connection)
            operator = OperatorIdentity(
                subject="qa-retention-persistence",
                name="리텐션 영속성 QA",
                auth_mode="integration-test",
                access_role="ADMIN",
            )
            expected_snooze = (
                datetime.now(timezone.utc) + timedelta(days=7)
            ).replace(second=0, microsecond=0)
            base_payload = {
                "model_version": sample["model_version"],
                "sample_id": sample["sample_id"],
                "decision": "변화 지켜보기",
                "note": "A06 롤백 검증 메모",
                "assignee_subject": operator.subject,
                "snooze_until": expected_snooze,
                "risk_type": None,
                "model_judgment": None,
                "expected_lock_version": None,
            }

            created = save_decision(
                rollback_engine, sample["user_id"], base_payload, operator
            )
            persisted = next(
                row
                for row in list_decisions(rollback_engine, sample["model_version"])
                if row["reviewerUserId"] == sample["user_id"]
            )
            expected_iso = expected_snooze.astimezone(timezone.utc).replace(
                tzinfo=None
            ).isoformat()
            if created["snoozeUntil"] != expected_iso:
                raise AssertionError("저장 응답의 snoozeUntil이 입력값과 다릅니다.")
            if persisted["snoozeUntil"] != expected_iso:
                raise AssertionError("재조회한 snoozeUntil이 저장값과 다릅니다.")

            replayed = save_decision(
                rollback_engine, sample["user_id"], base_payload, operator
            )
            replay_history = list_history(rollback_engine, sample["user_id"])
            if replayed["lockVersion"] != created["lockVersion"]:
                raise AssertionError("동일 요청 재전송이 lockVersion을 증가시켰습니다.")
            if len(replay_history) != 1:
                raise AssertionError("동일 요청 재전송이 History를 중복 생성했습니다.")

            updated_snooze = expected_snooze + timedelta(days=1)
            updated = save_decision(
                rollback_engine,
                sample["user_id"],
                {
                    **base_payload,
                    "note": "A07 변경 이력 검증 메모",
                    "snooze_until": updated_snooze,
                    "expected_lock_version": created["lockVersion"],
                },
                operator,
            )
            history = list_history(rollback_engine, sample["user_id"])
            latest = history[0]
            required_history = {
                "fromNote",
                "toNote",
                "fromAssigneeSubject",
                "toAssigneeSubject",
                "fromSnoozeUntil",
                "toSnoozeUntil",
            }
            missing = required_history.difference(latest)
            if missing:
                raise AssertionError(f"History 변경 상세가 누락됐습니다: {sorted(missing)}")
            if latest["fromSnoozeUntil"] != expected_iso:
                raise AssertionError("History의 이전 snoozeUntil이 저장값과 다릅니다.")
            if latest["toSnoozeUntil"] != updated["snoozeUntil"]:
                raise AssertionError("History의 변경 snoozeUntil이 저장값과 다릅니다.")

            try:
                save_decision(
                    rollback_engine,
                    sample["user_id"],
                    {
                        **base_payload,
                        "expected_lock_version": created["lockVersion"],
                    },
                    operator,
                )
            except RuntimeError:
                pass
            else:
                raise AssertionError("오래된 lockVersion 저장이 차단되지 않았습니다.")

            print(
                "PASS: snooze persistence, detailed history, and stale-write "
                f"protection ({sample['user_id']})"
            )
        finally:
            transaction.rollback()


if __name__ == "__main__":
    main()
