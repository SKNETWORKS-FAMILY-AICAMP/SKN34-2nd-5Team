"""리텐션 플레이북(playbooks.json) 조회.

export_playbooks() (scripts/export_frontend_data.py:604)와 대응한다.
modelJudgment은 DB 컬럼이 아니라 manager_decision을 DECISION_STATE_MAP으로
역매핑해 얻는다 — docs/ui/REACT_V04_DB_INTEGRATION_PLAN.md 2-3절 참고.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from api.insights_bridge import DECISION_STATE_MAP

_JUDGMENT_BY_DECISION = {
    decision: judgment for judgment, decision in DECISION_STATE_MAP.items()
}
_STATE_TO_JUDGMENT_LABEL = {0: "유지 우세", 1: "약화 우세", 2: "중단 우세"}


def get_playbooks(engine: Engine) -> list[dict]:
    with engine.connect() as conn:
        playbook_rows = conn.execute(
            text(
                """
                SELECT playbook_id, manager_decision, condition_text,
                       signals_text, primary_action, channel, needs_upgrade,
                       success_criteria
                FROM retention_playbooks
                WHERE is_active = 1
                ORDER BY display_order
                """
            )
        ).mappings().all()

        action_rows = conn.execute(
            text(
                """
                SELECT playbook_id, risk_type, sub_strategy_text
                FROM retention_playbook_risk_actions
                ORDER BY playbook_id, display_order
                """
            )
        ).mappings().all()

    actions_by_playbook: dict[str, list[dict]] = {}
    for row in action_rows:
        actions_by_playbook.setdefault(row["playbook_id"], []).append(
            {"riskType": row["risk_type"], "text": row["sub_strategy_text"]}
        )

    return [
        {
            "decision": row["manager_decision"],
            "condition": row["condition_text"],
            "signals": row["signals_text"],
            "primaryAction": row["primary_action"],
            "subStrategy": actions_by_playbook.get(row["playbook_id"], []),
            "channel": row["channel"],
            "needsUpgrade": row["needs_upgrade"],
            "successDraft": row["success_criteria"],
            "modelJudgment": _STATE_TO_JUDGMENT_LABEL.get(
                _JUDGMENT_BY_DECISION.get(row["manager_decision"])
            ),
        }
        for row in playbook_rows
    ]
