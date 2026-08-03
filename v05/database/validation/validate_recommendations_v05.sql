SELECT 'recommendation_version_rows' AS check_name, COUNT(*) AS row_count
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04' AND recommendation_version = 'v05_primary_cluster_radius';

SELECT 'missing_radius_context' AS check_name, COUNT(*) AS issue_count
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04'
  AND (observed_p90_radius_km IS NULL OR local_p90_radius_km IS NULL
       OR travel_outlier_count IS NULL OR activity_cluster_count IS NULL
       OR primary_cluster_business_count IS NULL);

SELECT 'invalid_cluster_context' AS check_name, COUNT(*) AS issue_count
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04'
  AND (activity_cluster_count < 1 OR primary_cluster_business_count < 1
       OR (activity_cluster_count = 1 AND travel_outlier_count <> 0));

SELECT 'invalid_local_radius' AS check_name, COUNT(*) AS issue_count
FROM reviewer_restaurant_recommendation
WHERE model_version = 'v04'
  AND (local_p90_radius_km <= 0
       OR search_radius_km + 0.01 < LEAST(local_p90_radius_km, 50)
       OR search_radius_km > 50 OR distance_km > search_radius_km + 0.01);

SELECT 'duplicate_business' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT sample_id, business_id, COUNT(*) AS row_count
    FROM reviewer_restaurant_recommendation
    WHERE model_version = 'v04'
    GROUP BY sample_id, business_id
    HAVING COUNT(*) > 1
) AS duplicates;
