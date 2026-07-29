from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from database.load.load_yelp_data import (
    build_bundle,
    expected_counts_for_frames,
    validate_expected_contract,
    validate_loaded_counts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FullDatabaseLoaderContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = build_bundle(PROJECT_ROOT)

    def test_full_bundle_contains_every_requested_version(self) -> None:
        counts = self.bundle.expected_version_counts

        self.assertEqual(
            counts["model_versions"],
            {"v02": 1, "v03": 1, "v04": 1},
        )
        self.assertEqual(counts["cohort_samples"], {"v04": 37_953})
        self.assertEqual(counts["model_predictions"], {"v04": 6_533})
        self.assertEqual(
            counts["model_validation_metrics"],
            {"v03": 9, "v04": 9},
        )
        self.assertEqual(
            counts["model_topk_metrics"],
            {"v03": 48, "v04": 48},
        )
        self.assertEqual(
            counts["model_binary_validation_metrics"],
            {"v02": 2},
        )
        self.assertEqual(
            counts["model_binary_topk_metrics"],
            {"v02": 16},
        )
        self.assertEqual(
            counts["feature_importance"],
            {"v02": 43, "v03": 43, "v04": 43},
        )
        self.assertEqual(
            counts["feature_group_importance"],
            {"v02": 3, "v03": 3, "v04": 3},
        )
        self.assertEqual(len(self.bundle.parent_rows), 4)
        self.assertEqual(len(self.bundle.risk_action_rows), 6)

    def test_missing_required_version_data_is_rejected(self) -> None:
        incomplete = {
            table_name: dict(version_counts)
            for table_name, version_counts in self.bundle.expected_version_counts.items()
        }
        del incomplete["model_topk_metrics"]["v03"]

        with self.assertRaisesRegex(ValueError, "필수 버전별 자료가 누락"):
            validate_expected_contract(incomplete)

    def test_post_load_count_mismatch_is_rejected(self) -> None:
        expected = self.bundle.expected_version_counts
        actual = {
            table_name: dict(version_counts)
            for table_name, version_counts in expected.items()
        }
        actual["feature_importance"]["v02"] -= 1

        with self.assertRaisesRegex(RuntimeError, "버전별 행 수 검증에 실패"):
            validate_loaded_counts(expected, actual)

    def test_frame_counter_combines_shared_tables_by_version(self) -> None:
        frames = [
            (
                "shared_metric",
                pd.DataFrame({"model_version": ["v04", "v04"]}),
            ),
            (
                "shared_metric",
                pd.DataFrame({"model_version": ["v03"]}),
            ),
        ]

        self.assertEqual(
            expected_counts_for_frames(frames),
            {"shared_metric": {"v03": 1, "v04": 2}},
        )


if __name__ == "__main__":
    unittest.main()
