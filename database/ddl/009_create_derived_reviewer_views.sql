CREATE OR REPLACE VIEW vw_regional_risk_summary AS
WITH city_counts AS (
    SELECT
        region.model_version,
        region.state,
        region.top_city,
        COUNT(*) AS city_reviewers
    FROM reviewer_region AS region
    WHERE region.top_city IS NOT NULL
      AND region.top_city <> ''
    GROUP BY
        region.model_version,
        region.state,
        region.top_city
),
ranked_cities AS (
    SELECT
        city_counts.*,
        ROW_NUMBER() OVER (
            PARTITION BY city_counts.model_version, city_counts.state
            ORDER BY
                city_counts.city_reviewers DESC,
                city_counts.top_city ASC
        ) AS city_rank
    FROM city_counts
),
regional_counts AS (
    SELECT
        region.model_version,
        region.state,
        COUNT(*) AS total_reviewers,
        SUM(prediction.predicted_state = 0) AS retained_count,
        SUM(prediction.predicted_state = 1) AS weakened_count,
        SUM(prediction.predicted_state = 2) AS stopped_count,
        SUM(prediction.predicted_state IN (1, 2)) AS high_risk_count,
        SUM(prediction.selected_for_crm) AS crm_targets
    FROM reviewer_region AS region
    JOIN model_predictions AS prediction
      ON prediction.model_version = region.model_version
     AND prediction.sample_id = region.sample_id
    GROUP BY region.model_version, region.state
)
SELECT
    regional_counts.model_version,
    regional_counts.state,
    ranked_cities.top_city,
    regional_counts.total_reviewers,
    regional_counts.retained_count,
    regional_counts.weakened_count,
    regional_counts.stopped_count,
    regional_counts.high_risk_count,
    regional_counts.high_risk_count
        / NULLIF(regional_counts.total_reviewers, 0) AS high_risk_rate,
    regional_counts.crm_targets,
    regional_counts.total_reviewers < 30 AS below_minimum
FROM regional_counts
LEFT JOIN ranked_cities
  ON ranked_cities.model_version = regional_counts.model_version
 AND ranked_cities.state = regional_counts.state
 AND ranked_cities.city_rank = 1;
