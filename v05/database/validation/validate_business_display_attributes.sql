-- Every issue_count returned by this file must be zero.

-- Display attributes cover both recommendation candidates and reviewer activity
-- businesses, so the table is intentionally a superset of recommendation IDs.
SELECT 'duplicate_business_attribute_key' AS check_name,
       COUNT(*) AS issue_count
FROM (
    SELECT business_id
    FROM business_display_attribute
    GROUP BY business_id
    HAVING COUNT(*) > 1
) AS duplicates;

SELECT 'missing_recommendation_business_attributes' AS check_name,
       COUNT(*) AS issue_count
FROM (
    SELECT DISTINCT recommendation.business_id
    FROM reviewer_restaurant_recommendation AS recommendation
    LEFT JOIN business_display_attribute AS attribute
      ON attribute.business_id = recommendation.business_id
    WHERE attribute.business_id IS NULL
) AS missing;

SELECT 'invalid_display_attribute_values' AS check_name,
       COUNT(*) AS issue_count
FROM business_display_attribute
WHERE is_open_snapshot NOT IN (0, 1)
   OR (price_range IS NOT NULL AND price_range NOT BETWEEN 1 AND 4)
   OR source_type <> 'yelp_open_dataset'
   OR (hours_json IS NOT NULL AND JSON_VALID(hours_json) = 0)
   OR (parking_json IS NOT NULL AND JSON_VALID(parking_json) = 0);

SELECT 'missing_recommendation_display_context' AS check_name,
       COUNT(*) AS issue_count
FROM business_display_attribute AS attribute
JOIN (
    SELECT DISTINCT business_id
    FROM reviewer_restaurant_recommendation
) AS recommendation
  ON recommendation.business_id = attribute.business_id
WHERE attribute.address IS NULL
  AND attribute.hours_json IS NULL
  AND attribute.price_range IS NULL
  AND attribute.takeout IS NULL
  AND attribute.delivery IS NULL
  AND attribute.reservations IS NULL;
