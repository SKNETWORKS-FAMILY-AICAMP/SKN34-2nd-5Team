from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PLAYBOOK_IDS = {
    "리뷰 다시 시작 유도": "review_restart",
    "리뷰 활동 늘리기": "review_activity",
    "변화 지켜보기": "monitor_change",
    "이번엔 제외": "exclude_now",
}
REQUIRED_FIELDS = {
    "condition",
    "signals",
    "primary_action",
    "sub_strategy",
    "channel",
    "needs_upgrade",
    "success_draft",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="리텐션 플레이북 기준 데이터를 MySQL에 적재합니다."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="SKN34-2nd-5Team 프로젝트 루트",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="기준 데이터 계약만 검증하고 DB에는 연결하지 않습니다.",
    )
    parser.add_argument(
        "--confirm-database",
        help="실제 연결된 DB 이름과 정확히 일치해야 적재를 진행합니다.",
    )
    return parser.parse_args()


def load_source(
    project_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    app_dir = project_root.resolve() / "archive" / "app_streamlit_v04"
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    from core.insights import DECISION_PLAYBOOKS, STRATEGIES

    return DECISION_PLAYBOOKS, STRATEGIES


def _require_text(value: Any, label: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{label} 값이 비어 있습니다.")
    return text


def build_reference_rows(
    playbooks: dict[str, dict[str, Any]],
    strategies: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if set(playbooks) != set(PLAYBOOK_IDS):
        raise ValueError(
            "DECISION_PLAYBOOKS와 PLAYBOOK_IDS의 관리자 판단 목록이 다릅니다: "
            + json.dumps(
                {
                    "playbooks_only": sorted(set(playbooks) - set(PLAYBOOK_IDS)),
                    "ids_only": sorted(set(PLAYBOOK_IDS) - set(playbooks)),
                },
                ensure_ascii=False,
            )
        )

    parent_rows: list[dict[str, Any]] = []
    risk_action_rows: list[dict[str, Any]] = []

    for display_order, (manager_decision, playbook_id) in enumerate(
        PLAYBOOK_IDS.items(), start=1
    ):
        entry = playbooks[manager_decision]
        missing = REQUIRED_FIELDS - set(entry)
        if missing:
            raise ValueError(
                f"{manager_decision}: 필수 플레이북 필드 누락: {sorted(missing)}"
            )
        if not isinstance(entry["sub_strategy"], dict):
            raise ValueError(f"{manager_decision}: sub_strategy는 dict여야 합니다.")

        parent_rows.append(
            {
                "playbook_id": playbook_id,
                "manager_decision": manager_decision,
                "title": manager_decision,
                "condition_text": _require_text(
                    entry["condition"], f"{manager_decision}.condition"
                ),
                "signals_text": _require_text(
                    entry["signals"], f"{manager_decision}.signals"
                ),
                "primary_action": _require_text(
                    entry["primary_action"], f"{manager_decision}.primary_action"
                ),
                "channel": _require_text(
                    entry["channel"], f"{manager_decision}.channel"
                ),
                "needs_upgrade": _require_text(
                    entry["needs_upgrade"], f"{manager_decision}.needs_upgrade"
                ),
                "success_criteria": _require_text(
                    entry["success_draft"], f"{manager_decision}.success_draft"
                ),
                "display_order": display_order,
                "is_active": 1,
            }
        )

        for action_order, (risk_type, text) in enumerate(
            entry["sub_strategy"].items(), start=1
        ):
            if risk_type not in strategies:
                raise ValueError(
                    f"{manager_decision}: 정의되지 않은 위험 유형 {risk_type!r}"
                )
            risk_action_rows.append(
                {
                    "playbook_id": playbook_id,
                    "risk_type": risk_type,
                    "sub_strategy_text": _require_text(
                        text, f"{manager_decision}.{risk_type}"
                    ),
                    "display_order": action_order,
                }
            )

    if len(parent_rows) != 4 or len(risk_action_rows) != 6:
        raise ValueError(
            "플레이북 기준 행 수가 계약과 다릅니다: "
            f"playbooks={len(parent_rows)}, risk_actions={len(risk_action_rows)}"
        )
    return parent_rows, risk_action_rows


def _upsert_playbook(connection, row: dict[str, Any]) -> None:
    exists = connection.exec_driver_sql(
        "SELECT COUNT(*) FROM retention_playbooks WHERE playbook_id = %s",
        (row["playbook_id"],),
    ).scalar_one()
    params = (
        row["manager_decision"],
        row["title"],
        row["condition_text"],
        row["signals_text"],
        row["primary_action"],
        row["channel"],
        row["needs_upgrade"],
        row["success_criteria"],
        row["display_order"],
        row["is_active"],
    )
    if exists:
        connection.exec_driver_sql(
            """
            UPDATE retention_playbooks
            SET manager_decision = %s,
                title = %s,
                condition_text = %s,
                signals_text = %s,
                primary_action = %s,
                channel = %s,
                needs_upgrade = %s,
                success_criteria = %s,
                display_order = %s,
                is_active = %s
            WHERE playbook_id = %s
            """,
            params + (row["playbook_id"],),
        )
        return

    connection.exec_driver_sql(
        """
        INSERT INTO retention_playbooks (
            playbook_id,
            manager_decision,
            title,
            condition_text,
            signals_text,
            primary_action,
            channel,
            needs_upgrade,
            success_criteria,
            display_order,
            is_active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (row["playbook_id"],) + params,
    )


def seed_reference_data(
    connection,
    parent_rows: list[dict[str, Any]],
    risk_action_rows: list[dict[str, Any]],
) -> None:
    for row in parent_rows:
        _upsert_playbook(connection, row)

    actions_by_playbook = {row["playbook_id"]: [] for row in parent_rows}
    for row in risk_action_rows:
        actions_by_playbook[row["playbook_id"]].append(row)

    for playbook_id, actions in actions_by_playbook.items():
        connection.exec_driver_sql(
            """
            DELETE FROM retention_playbook_risk_actions
            WHERE playbook_id = %s
            """,
            (playbook_id,),
        )
        for row in actions:
            connection.exec_driver_sql(
                """
                INSERT INTO retention_playbook_risk_actions (
                    playbook_id,
                    risk_type,
                    sub_strategy_text,
                    display_order
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    row["playbook_id"],
                    row["risk_type"],
                    row["sub_strategy_text"],
                    row["display_order"],
                ),
            )


def seed_mysql(
    project_root: Path,
    confirm_database: str,
    parent_rows: list[dict[str, Any]],
    risk_action_rows: list[dict[str, Any]],
) -> None:
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from database.load.load_v04 import create_engine_from_env, database_name

    engine = create_engine_from_env(project_root)
    try:
        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != confirm_database:
                raise RuntimeError(
                    f"연결 DB({actual_database})와 확인값"
                    f"({confirm_database})이 다릅니다."
                )
            seed_reference_data(connection, parent_rows, risk_action_rows)

            managed_ids = tuple(row["playbook_id"] for row in parent_rows)
            placeholders = ", ".join(["%s"] * len(managed_ids))
            playbook_count = int(
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM retention_playbooks "
                    f"WHERE playbook_id IN ({placeholders})",
                    managed_ids,
                ).scalar_one()
            )
            action_count = int(
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM retention_playbook_risk_actions "
                    f"WHERE playbook_id IN ({placeholders})",
                    managed_ids,
                ).scalar_one()
            )
            if playbook_count != len(parent_rows) or action_count != len(
                risk_action_rows
            ):
                raise RuntimeError(
                    "적재 후 기준 행 수가 다릅니다: "
                    f"playbooks={playbook_count}, risk_actions={action_count}"
                )
    finally:
        engine.dispose()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    try:
        playbooks, strategies = load_source(project_root)
        parent_rows, risk_action_rows = build_reference_rows(
            playbooks, strategies
        )
        print(
            json.dumps(
                {
                    "retention_playbooks": len(parent_rows),
                    "retention_playbook_risk_actions": len(risk_action_rows),
                    "manager_decisions": [
                        row["manager_decision"] for row in parent_rows
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if args.dry_run:
            print("dry-run complete: DB 변경 없음")
            return 0
        if not args.confirm_database:
            raise RuntimeError(
                "오적재 방지를 위해 --confirm-database에 대상 DB 이름을 입력해야 합니다."
            )
        seed_mysql(
            project_root,
            args.confirm_database,
            parent_rows,
            risk_action_rows,
        )
        print("retention playbook reference data seed complete")
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
