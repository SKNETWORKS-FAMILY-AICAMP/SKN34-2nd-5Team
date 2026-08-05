from __future__ import annotations

from pathlib import Path
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
MODEL_VERSION = "v05_05_dl"


class UnifiedOperatingContextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.region = pd.read_parquet(
            PROCESSED / f"reviewer_region_{MODEL_VERSION}.parquet"
        )
        cls.history = pd.read_parquet(
            PROCESSED / f"reviewer_region_history_{MODEL_VERSION}.parquet"
        )
        cls.entry = pd.read_parquet(
            PROCESSED / f"reviewer_operating_entry_{MODEL_VERSION}.parquet"
        )
        cls.supply = pd.read_parquet(
            PROCESSED / f"regional_review_supply_{MODEL_VERSION}.parquet"
        )
        cls.weekday = pd.read_parquet(
            PROCESSED / f"regional_weekday_pattern_{MODEL_VERSION}.parquet"
        )
        cls.city_supply = pd.read_parquet(
            PROCESSED / f"city_review_supply_{MODEL_VERSION}.parquet"
        )
        cls.city_weekday = pd.read_parquet(
            PROCESSED / f"city_weekday_pattern_{MODEL_VERSION}.parquet"
        )

    def test_current_operating_cohort_is_complete(self) -> None:
        self.assertEqual(len(self.region), 6_533)
        self.assertEqual(len(self.entry), 6_533)
        self.assertSetEqual(set(self.region.sample_id), set(self.entry.sample_id))
        self.assertTrue((self.entry.first_selection_year <= 2018).all())

    def test_full_history_is_preserved_as_audit_artifact(self) -> None:
        self.assertEqual(len(self.history), 37_953)
        self.assertEqual(set(self.history.model_version), {MODEL_VERSION})
        self.assertEqual(self.history.selection_year.max(), 2018)

    def test_weekday_counts_match_selection_year_supply(self) -> None:
        selection = self.supply.loc[
            self.supply.activity_year.eq(2018), ["state", "review_count"]
        ].set_index("state")["review_count"]
        weekday_totals = self.weekday.groupby("state")["review_count"].sum()
        pd.testing.assert_series_equal(
            weekday_totals.sort_index(), selection.sort_index(), check_dtype=False
        )
        self.assertTrue(self.weekday.groupby("state").iso_weekday.nunique().eq(7).all())

    def test_unified_scope_does_not_reduce_regional_supply(self) -> None:
        legacy = pd.read_parquet(
            PROCESSED / "regional_review_supply_v04.parquet"
        )
        legacy = legacy.loc[legacy.activity_year.eq(2018)].set_index("state").review_count
        unified = self.supply.loc[
            self.supply.activity_year.eq(2018)
        ].set_index("state").review_count
        self.assertTrue((unified >= legacy).all())
        self.assertTrue((unified > legacy).any())

    def test_city_weekday_counts_match_selection_year_supply(self) -> None:
        selection = self.city_supply.loc[
            self.city_supply.activity_year.eq(2018),
            ["state", "city_key", "review_count"],
        ].set_index(["state", "city_key"])["review_count"]
        weekday_totals = self.city_weekday.groupby(
            ["state", "city_key"]
        )["review_count"].sum()
        pd.testing.assert_series_equal(
            weekday_totals.sort_index(), selection.sort_index(), check_dtype=False
        )
        self.assertTrue(
            self.city_weekday.groupby(["state", "city_key"])
            .iso_weekday.nunique().le(7).all()
        )


if __name__ == "__main__":
    unittest.main()
