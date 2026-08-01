"""Build cohort-independent annual restaurant review supply by v04 region.

Unlike the removed reviewer-cohort metric, this artifact counts every review
of an eligible restaurant in each business's state.  It is capped at the v04
test selection year (2018), so target/future activity cannot leak into the
operational context shown with the v04 model.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
MODEL_VERSION = "v04"


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def main() -> None:
    interim = ROOT / "data" / "interim"
    processed = ROOT / "data" / "processed"
    config_path = ROOT / "configs" / "analysis_config_v04.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    first_year = int(config["cohort"]["minimum_selection_year"]) - 1
    last_year = int(config["cohort"]["test_selection_year"])

    region_source = pd.read_parquet(
        processed / "reviewer_region_v04.parquet", columns=["state"]
    )
    regions = sorted(region_source["state"].dropna().astype(str).unique())
    if len(regions) != 14:
        raise ValueError(f"expected 14 v04 regions, found {len(regions)}: {regions}")
    region_sql = ", ".join(f"'{state.replace("'", "''")}'" for state in regions)

    reviews = interim / "restaurant_reviews.parquet"
    businesses = interim / "restaurant_businesses.parquet"
    output = processed / "regional_review_supply_v04.parquet"
    connection = duckdb.connect()
    frame = connection.execute(
        f"""
        WITH annual AS (
            SELECT
                business.state,
                YEAR(CAST(review.date AS TIMESTAMP)) AS activity_year,
                COUNT(*) AS review_count,
                COUNT(DISTINCT review.user_id) AS active_reviewer_count,
                COUNT(DISTINCT review.business_id) AS active_business_count
            FROM read_parquet('{sql_path(reviews)}') AS review
            INNER JOIN read_parquet('{sql_path(businesses)}') AS business
                ON business.business_id = review.business_id
            WHERE business.state IN ({region_sql})
              AND YEAR(CAST(review.date AS TIMESTAMP)) BETWEEN {first_year} AND {last_year}
            GROUP BY business.state, activity_year
        ), with_previous AS (
            SELECT
                *,
                LAG(review_count) OVER (
                    PARTITION BY state ORDER BY activity_year
                ) AS previous_year_review_count
            FROM annual
        )
        SELECT
            '{MODEL_VERSION}' AS model_version,
            state,
            CAST(activity_year AS SMALLINT) AS activity_year,
            CAST(review_count AS BIGINT) AS review_count,
            CAST(active_reviewer_count AS BIGINT) AS active_reviewer_count,
            CAST(active_business_count AS BIGINT) AS active_business_count,
            CAST(previous_year_review_count AS BIGINT) AS previous_year_review_count,
            CAST(review_count - previous_year_review_count AS BIGINT)
                AS yoy_review_change,
            CASE WHEN previous_year_review_count > 0
                THEN (review_count - previous_year_review_count)
                     / previous_year_review_count::DOUBLE
            END AS yoy_review_change_rate,
            activity_year = {last_year - 1} AS is_comparison_year,
            activity_year = {last_year} AS is_selection_year,
            'all_restaurant_reviews_by_business_state' AS calculation_method
        FROM with_previous
        ORDER BY state, activity_year
        """
    ).fetchdf()
    connection.close()

    key = ["model_version", "state", "activity_year"]
    if frame.duplicated(key).any():
        raise ValueError("duplicate regional review-supply key")
    if set(frame["state"]) != set(regions):
        raise ValueError("one or more v04 regions have no review-supply rows")
    if int(frame["activity_year"].max()) != last_year:
        raise ValueError("selection-year review supply is missing")
    frame.to_parquet(output, index=False)
    print(
        f"wrote {len(frame):,} state-year rows ({first_year}-{last_year}, "
        f"{len(regions)} regions) to {output}"
    )


if __name__ == "__main__":
    main()
