SELECT 'business_photo_rows' AS check_name, COUNT(*) AS row_count
FROM business_photo;

SELECT 'businesses_with_photos' AS check_name, COUNT(DISTINCT business_id) AS row_count
FROM business_photo;

SELECT 'duplicate_display_rank' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT business_id, display_rank, COUNT(*) AS row_count
    FROM business_photo
    GROUP BY business_id, display_rank
    HAVING COUNT(*) > 1
) AS duplicates;

SELECT 'recommended_business_without_photo' AS check_name, COUNT(*) AS row_count
FROM (
    SELECT DISTINCT recommendation.business_id
    FROM reviewer_restaurant_recommendation AS recommendation
    LEFT JOIN business_photo AS photo
      ON photo.business_id = recommendation.business_id
    WHERE recommendation.model_version = 'v04' AND photo.business_id IS NULL
) AS missing;
