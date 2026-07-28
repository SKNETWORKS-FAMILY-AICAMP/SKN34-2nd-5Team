from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from pipeline.v04.derived_reviewer_activity import (
    derive_outputs,
    derived_paths,
    validate_outputs,
)


class DerivedReviewerActivityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profiles = pd.DataFrame(
            [
                {
                    "sample_id": "user-1_2018",
                    "user_id": "user-1",
                    "comparison_year": 2017,
                    "selection_year": 2018,
                    "baseline_review_count": 3,
                    "recent_review_count": 1,
                },
                {
                    "sample_id": "user-2_2018",
                    "user_id": "user-2",
                    "comparison_year": 2017,
                    "selection_year": 2018,
                    "baseline_review_count": 0,
                    "recent_review_count": 2,
                },
            ]
        )
        self.reviews = pd.DataFrame(
            [
                {
                    "user_id": "user-1",
                    "business_id": "pa-1",
                    "date": "2017-01-03",
                },
                {
                    "user_id": "user-1",
                    "business_id": "pa-1",
                    "date": "2017-02-03",
                },
                {
                    "user_id": "user-1",
                    "business_id": "pa-2",
                    "date": "2017-02-15",
                },
                {
                    "user_id": "user-1",
                    "business_id": "nj-1",
                    "date": "2018-03-01",
                },
                {
                    "user_id": "user-1",
                    "business_id": "pa-1",
                    "date": "2019-01-01",
                },
                {
                    "user_id": "user-2",
                    "business_id": "ab-1",
                    "date": "2018-04-02",
                },
                {
                    "user_id": "user-2",
                    "business_id": "ab-2",
                    "date": "2018-04-20",
                },
            ]
        )
        self.businesses = pd.DataFrame(
            [
                {
                    "business_id": "pa-1",
                    "city": "Philadelphia",
                    "state": "PA",
                },
                {
                    "business_id": "pa-2",
                    "city": "Pittsburgh",
                    "state": "PA",
                },
                {
                    "business_id": "nj-1",
                    "city": "Cherry Hill",
                    "state": "NJ",
                },
                {
                    "business_id": "ab-1",
                    "city": "Edmonton",
                    "state": "AB",
                },
                {
                    "business_id": "ab-2",
                    "city": "Calgary",
                    "state": "AB",
                },
            ]
        )

    def test_derives_region_and_monthly_activity_without_target_year(self) -> None:
        region, monthly = derive_outputs(
            self.profiles,
            self.reviews,
            self.businesses,
        )

        observed_regions = region.set_index("sample_id").to_dict("index")
        self.assertEqual(observed_regions["user-1_2018"]["state"], "PA")
        self.assertEqual(
            observed_regions["user-1_2018"]["top_city"],
            "Philadelphia",
        )
        self.assertEqual(observed_regions["user-2_2018"]["state"], "AB")
        self.assertEqual(
            observed_regions["user-2_2018"]["top_city"],
            "Calgary",
        )

        self.assertNotIn("2019-01", set(monthly["year_month"]))
        totals = monthly.groupby("sample_id")["review_count"].sum().to_dict()
        self.assertEqual(totals, {"user-1_2018": 4, "user-2_2018": 2})

        summary = validate_outputs(
            self.profiles,
            region,
            monthly,
            expected_profile_rows=2,
        )
        self.assertEqual(summary["region_codes"], ["AB", "PA"])
        self.assertEqual(summary["monthly_samples"], 2)

    def test_validation_rejects_target_year_month(self) -> None:
        region, monthly = derive_outputs(
            self.profiles,
            self.reviews,
            self.businesses,
        )
        invalid = monthly.copy()
        invalid.loc[0, "year_month"] = "2019-01"

        with self.assertRaisesRegex(ValueError, "관찰 구간 밖"):
            validate_outputs(
                self.profiles,
                region,
                invalid,
                expected_profile_rows=2,
            )

    def test_legacy_additional_review_filename_is_supported(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            interim = root / "data" / "interim"
            interim.mkdir(parents=True)
            legacy = interim / "additional_culinary_reviews_v02.parquet"
            legacy.touch()

            self.assertEqual(
                derived_paths(root).additional_reviews,
                legacy,
            )

    def test_frontend_export_preserves_region_and_monthly_shape(self) -> None:
        from scripts.export_frontend_data import (
            export_monthly_activity,
            export_regional,
        )

        profiles = self.profiles.assign(
            predicted_state=[1, 2],
            crm_target=[1, 0],
        )
        region, monthly = derive_outputs(
            profiles,
            self.reviews,
            self.businesses,
        )

        regional_json = export_regional(profiles, region)
        self.assertTrue(regional_json["available"])
        self.assertEqual(regional_json["coveredReviewers"], 2)
        self.assertEqual(
            {row["region"] for row in regional_json["regions"]},
            {"AB", "PA"},
        )

        monthly_json = export_monthly_activity(profiles, monthly)
        self.assertEqual(set(monthly_json), {"user-1", "user-2"})
        self.assertEqual(
            sum(row["reviewCount"] for row in monthly_json["user-1"]),
            4,
        )


if __name__ == "__main__":
    unittest.main()
