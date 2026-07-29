from __future__ import annotations

import unittest
from pathlib import Path

from database.load.seed_reference_data import (
    PLAYBOOK_IDS,
    build_reference_rows,
    load_source,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReferenceDataSeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        playbooks, strategies = load_source(PROJECT_ROOT)
        cls.parent_rows, cls.risk_action_rows = build_reference_rows(
            playbooks, strategies
        )

    def test_playbook_parent_contract(self) -> None:
        self.assertEqual(len(self.parent_rows), 4)
        self.assertEqual(
            {row["playbook_id"] for row in self.parent_rows},
            set(PLAYBOOK_IDS.values()),
        )
        self.assertEqual(
            [row["display_order"] for row in self.parent_rows],
            [1, 2, 3, 4],
        )
        for row in self.parent_rows:
            self.assertTrue(row["condition_text"])
            self.assertTrue(row["signals_text"])
            self.assertTrue(row["needs_upgrade"])
            self.assertTrue(row["success_criteria"])

    def test_risk_action_child_contract(self) -> None:
        self.assertEqual(len(self.risk_action_rows), 6)
        counts = {
            playbook_id: sum(
                row["playbook_id"] == playbook_id
                for row in self.risk_action_rows
            )
            for playbook_id in PLAYBOOK_IDS.values()
        }
        self.assertEqual(
            counts,
            {
                "review_restart": 2,
                "review_activity": 3,
                "monitor_change": 1,
                "exclude_now": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
