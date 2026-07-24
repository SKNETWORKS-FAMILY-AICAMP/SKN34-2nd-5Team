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
        captured = self.profiles.loc[
            self.profiles["crm_target"].eq(1),
            "churn",
        ].sum()
        self.assertEqual(int(captured), 346)

    def test_risk_tier_counts(self) -> None:
        expected = {
            "긴급 관리": 208,
            "집중 관리": 624,
            "관찰 대상": 831,
            "일반": 2_494,
        }
        observed = self.profiles["risk_tier"].value_counts().to_dict()
        self.assertEqual(observed, expected)

    def test_reviewer_explanation_contract(self) -> None:
        row = self.profiles.iloc[0]
        self.assertEqual(len(risk_signals(row)), 5)
        self.assertTrue(strategy_for(row)["primary"])


if __name__ == "__main__":
    unittest.main()

