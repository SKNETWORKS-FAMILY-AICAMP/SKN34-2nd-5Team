-- v05 city operating context validation.
-- Every issue_count must be 0 unless an expected value is shown explicitly.

SELECT 'city_supply_rows' AS check_name, COUNT(*) AS observed,
       6902 AS expected
FROM city_review_supply
WHERE model_version = 'v04';

SELECT 'city_newcomer_rows' AS check_name, COUNT(*) AS observed,
       1424 AS expected
FROM city_newcomer
WHERE model_version = 'v04';

SELECT 'eligible_2018_cities' AS check_name, COUNT(*) AS observed,
       311 AS expected
FROM city_review_supply
WHERE model_version = 'v04'
  AND activity_year = 2018
  AND minimum_sample_met = 1;

SELECT 'eligible_2018_states' AS check_name, COUNT(DISTINCT state) AS observed,
       14 AS expected
FROM city_review_supply
WHERE model_version = 'v04'
  AND activity_year = 2018
  AND minimum_sample_met = 1;

SELECT 'duplicate_city_supply_key' AS check_name,
       COUNT(*) - COUNT(DISTINCT model_version, state, city_key, activity_year)
           AS issue_count
FROM city_review_supply
WHERE model_version = 'v04';

SELECT 'duplicate_city_newcomer_key' AS check_name,
       COUNT(*) - COUNT(DISTINCT model_version, selection_year, state, city_key)
           AS issue_count
FROM city_newcomer
WHERE model_version = 'v04';

SELECT 'future_data_leak' AS check_name, COUNT(*) AS issue_count
FROM city_review_supply
WHERE model_version = 'v04' AND activity_year > 2018;

SELECT 'sample_flag_mismatch' AS check_name, COUNT(*) AS issue_count
FROM city_review_supply
WHERE model_version = 'v04'
  AND minimum_sample_met <>
      (active_reviewer_count >= 30 AND review_count >= 100);

SELECT 'city_vs_region_supply_mismatch' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT city.state, city.activity_year
    FROM (
        SELECT state, activity_year, SUM(review_count) AS review_count
        FROM city_review_supply
        WHERE model_version = 'v04'
        GROUP BY state, activity_year
    ) AS city
    INNER JOIN regional_review_supply AS region
       ON region.model_version = 'v04'
      AND region.state = city.state
      AND region.activity_year = city.activity_year
    WHERE city.review_count <> region.review_count
) AS mismatches;

SELECT 'city_vs_region_newcomer_mismatch' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT city.selection_year, city.state
    FROM (
        SELECT selection_year, state, SUM(new_power_reviewers) AS newcomer_count
        FROM city_newcomer
        WHERE model_version = 'v04'
        GROUP BY selection_year, state
    ) AS city
    INNER JOIN regional_newcomer AS region
       ON region.model_version = 'v04'
      AND region.selection_year = city.selection_year
      AND region.state = city.state
    WHERE city.newcomer_count <> region.new_power_reviewers
) AS mismatches;

SELECT 'selection_year_newcomers' AS check_name,
       SUM(new_power_reviewers) AS observed, 3553 AS expected
FROM city_newcomer
WHERE model_version = 'v04' AND selection_year = 2018;

