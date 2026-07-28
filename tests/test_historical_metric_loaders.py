from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from database.load.historical_metrics import (
    load_v02_bundle,
    load_v03_bundle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def frame_map(bundle):
    return {name: frame for name, frame in bundle.frames}


class HistoricalMetricLoaderTest(unittest.TestCase):
    def test_v03_reuses_multiclass_metric_tables(self) -> None:
        bundle = load_v03_bundle(PROJECT_ROOT)
        frames = frame_map(bundle)

        self.assertEqual(bundle.summary["test_samples"], 4_157)
        self.assertEqual(len(frames["model_validation_metrics"]), 9)
        self.assertEqual(len(frames["model_topk_metrics"]), 48)
        self.assertEqual(len(frames["model_confusion_matrix"]), 63)
        self.assertNotIn(
            "decision_policy",
            frames["model_confusion_matrix"].columns,
        )

        final_confusion = frames["model_confusion_matrix"].loc[
            frames["model_confusion_matrix"]["split"].eq("final_test")
        ]
        self.assertEqual(int(final_confusion["users"].sum()), 4_157)

        feature = frames["feature_importance"]
        group = frames["feature_group_importance"]
        self.assertTrue(feature["model_version"].eq("v03").all())
        self.assertTrue(feature["repeats"].eq(20).all())
        self.assertTrue(group["method"].eq("group_ablation_retrain").all())
        self.assertTrue(group["importance_std"].isna().all())

    def test_v02_uses_binary_metrics_and_reuses_shared_tables(self) -> None:
        bundle = load_v02_bundle(PROJECT_ROOT)
        frames = frame_map(bundle)

        binary_validation = frames["model_binary_validation_metrics"]
        binary_topk = frames["model_binary_topk_metrics"]
        confusion = frames["model_confusion_matrix"]

        self.assertEqual(set(binary_validation["split"]), {"validation", "final_test"})
        self.assertEqual(len(binary_topk), 16)
        self.assertEqual(len(confusion), 8)
        final_confusion = confusion.loc[confusion["split"].eq("final_test")]
        self.assertEqual(int(final_confusion["users"].sum()), 4_157)

        top20 = binary_topk.loc[
            binary_topk["split"].eq("final_test")
            & np.isclose(binary_topk["target_rate"], 0.20)
        ]
        self.assertEqual(int(top20.iloc[0]["target_users"]), 832)
        self.assertEqual(int(top20.iloc[0]["captured_churn_users"]), 346)

        self.assertEqual(len(frames["feature_importance"]), 43)
        self.assertEqual(len(frames["feature_group_importance"]), 3)
        self.assertTrue(
            frames["feature_importance"]["method"]
            .eq("single_feature_permutation")
            .all()
        )
        self.assertTrue(
            frames["feature_group_importance"]["method"]
            .eq("joint_group_permutation")
            .all()
        )

    def test_report_only_versions_do_not_fabricate_model_hash(self) -> None:
        for bundle in [
            load_v02_bundle(PROJECT_ROOT),
            load_v03_bundle(PROJECT_ROOT),
        ]:
            versions = frame_map(bundle)["model_versions"]
            self.assertIsNone(versions.iloc[0]["model_sha256"])
            metadata = json.loads(versions.iloc[0]["metadata_json"])
            self.assertFalse(metadata["model_artifact_available"])
            self.assertEqual(len(metadata["source_bundle_sha256"]), 64)
            self.assertTrue(metadata["source_files"])


if __name__ == "__main__":
    unittest.main()
