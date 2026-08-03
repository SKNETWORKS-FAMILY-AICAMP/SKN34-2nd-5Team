-- Run after the v05 derived-table reloaders. Every issue_count must be 0.
-- The recommendation reloader already asserts Parquet row count = loaded DB row
-- count inside one transaction, so this SQL validates the resulting data contract
-- rather than pinning a legitimate algorithm result to one historical row count.

SELECT 'recommendation_empty' AS check_name,
       CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END AS issue_count
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04'
UNION ALL
SELECT 'region_history_row_count', ABS(COUNT(*) - 37953)
FROM reviewer_region_history WHERE model_version = 'v04'
UNION ALL
SELECT 'newcomer_row_count', ABS(COUNT(*) - 126)
FROM regional_newcomer WHERE model_version = 'v04'
UNION ALL
SELECT 'review_supply_row_count', ABS(COUNT(*) - 140)
FROM regional_review_supply WHERE model_version = 'v04';

SELECT 'recommendation_over_three' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT sample_id
    FROM reviewer_restaurant_recommendation
    WHERE model_version = 'v04'
    GROUP BY sample_id HAVING COUNT(*) > 3
) AS issues
UNION ALL
SELECT 'recommendation_duplicate_business', COUNT(*)
FROM (
    SELECT sample_id, business_id
    FROM reviewer_restaurant_recommendation
    WHERE model_version = 'v04'
    GROUP BY sample_id, business_id HAVING COUNT(*) > 1
) AS issues
UNION ALL
SELECT 'recommendation_duplicate_rank', COUNT(*)
FROM (
    SELECT sample_id, recommendation_rank
    FROM reviewer_restaurant_recommendation
    WHERE model_version = 'v04'
    GROUP BY sample_id, recommendation_rank HAVING COUNT(*) > 1
) AS issues
UNION ALL
SELECT 'recommendation_version_mismatch', COUNT(*)
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04'
  AND recommendation_version <> 'v05_primary_cluster_radius'
UNION ALL
SELECT 'recommendation_invalid_contract', COUNT(*)
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04'
  AND (distance_km < 0 OR search_radius_km > 50 OR stars < 3.5
       OR distance_km > search_radius_km + 0.01
       OR review_count < 10 OR recommendation_rank NOT BETWEEN 1 AND 3)
UNION ALL
SELECT 'recommendation_missing_cluster_context', COUNT(*)
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04'
  AND (recommendation_version IS NULL OR observed_p90_radius_km IS NULL
       OR local_p90_radius_km IS NULL OR travel_outlier_count IS NULL
       OR activity_cluster_count IS NULL OR primary_cluster_business_count IS NULL)
UNION ALL
SELECT 'recommendation_invalid_cluster_context', COUNT(*)
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04'
  AND (local_p90_radius_km <= 0 OR activity_cluster_count < 1
       OR primary_cluster_business_count < 1
       OR (activity_cluster_count = 1 AND travel_outlier_count <> 0))
UNION ALL
SELECT 'recommendation_orphan_sample', COUNT(*)
FROM reviewer_restaurant_recommendation AS recommendation
LEFT JOIN cohort_samples AS cohort
  ON cohort.model_version = recommendation.model_version
 AND cohort.sample_id = recommendation.sample_id
WHERE recommendation.model_version = 'v04' AND cohort.sample_id IS NULL;

SELECT 'region_history_duplicate_sample' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT sample_id FROM reviewer_region_history
    WHERE model_version = 'v04'
    GROUP BY sample_id HAVING COUNT(*) > 1
) AS issues
UNION ALL
SELECT 'region_history_invalid_time', COUNT(*)
FROM reviewer_region_history
WHERE model_version = 'v04' AND comparison_year + 1 <> selection_year
UNION ALL
SELECT 'region_history_2018_mismatch', COUNT(*)
FROM reviewer_region_history AS history
JOIN reviewer_region AS published
  ON published.model_version = history.model_version
 AND published.sample_id = history.sample_id
WHERE history.model_version = 'v04' AND history.selection_year = 2018
  AND (history.state <> published.state
       OR NOT (history.top_city <=> published.top_city));

SELECT 'newcomer_total_mismatch' AS check_name,
       ABS(SUM(new_power_reviewers) - 23524) AS issue_count
FROM regional_newcomer WHERE model_version = 'v04'
UNION ALL
SELECT 'review_supply_future_year', COUNT(*)
FROM regional_review_supply
WHERE model_version = 'v04' AND activity_year > 2018
UNION ALL
SELECT 'review_supply_region_count', ABS(COUNT(DISTINCT state) - 14)
FROM regional_review_supply WHERE model_version = 'v04'
UNION ALL
SELECT 'review_supply_2018_total_mismatch',
       ABS(SUM(review_count) - 610672)
FROM regional_review_supply
WHERE model_version = 'v04' AND activity_year = 2018;
