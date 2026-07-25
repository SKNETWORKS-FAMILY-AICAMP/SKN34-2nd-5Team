from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from core.demo_data import build_demo_data  # noqa: E402
from core.insights import enrich_profiles, risk_signals, strategy_for  # noqa: E402


class DemoContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = build_demo_data()
        self.profiles = enrich_profiles(self.data.reviewer_profiles)

    def test_validated_test_counts(self) -> None:
        self.assertEqual(len(self.profiles), 4_157)
        self.assertEqual(int(self.profiles["churn"].sum()), 670)
        self.assertEqual(int(self.profiles["crm_target"].sum()), 832)
        target = self.profiles.loc[self.profiles["crm_target"].eq(1)]
        self.assertEqual(int(target["retention_state"].ne(0).sum()), 773)
        self.assertEqual(int(target["retention_state"].eq(2).sum()), 329)
        self.assertEqual(int(target["retention_state"].eq(1).sum()), 444)

    def test_retention_state_counts(self) -> None:
        expected = {
            "파워 지위 유지": 1_539,
            "파워 지위 약화": 1_948,
            "리뷰 활동 중단": 670,
        }
        observed = self.profiles["retention_state_label"].value_counts().to_dict()
        self.assertEqual(observed, expected)

        predicted = self.profiles["predicted_state_label"].value_counts().to_dict()
        self.assertEqual(
            predicted,
            {
                "파워 지위 약화": 1_757,
                "파워 지위 유지": 1_400,
                "리뷰 활동 중단": 1_000,
            },
        )

    def test_multiclass_scores_form_priority_score(self) -> None:
        score_sum = (
            self.profiles["retained_score"]
            + self.profiles["weakened_score"]
            + self.profiles["stopped_score"]
        )
        self.assertTrue((score_sum.round(10) == 1).all())
        priority = self.profiles["weakened_score"] + self.profiles["stopped_score"]
        self.assertTrue(
            (priority.round(10) == self.profiles["priority_score"].round(10)).all()
        )

    def test_reviewer_explanation_contract(self) -> None:
        row = self.profiles.iloc[0]
        self.assertEqual(len(risk_signals(row)), 5)
        self.assertTrue(strategy_for(row)["primary"])


if __name__ == "__main__":
    unittest.main()
