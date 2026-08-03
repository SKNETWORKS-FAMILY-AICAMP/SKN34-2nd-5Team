-- Travel-aware context for the v05 operational recommendation derivation.
-- The model_version remains v04 because the predictive model is unchanged.

ALTER TABLE reviewer_restaurant_recommendation
    ADD COLUMN recommendation_version VARCHAR(32)
        CHARACTER SET ascii COLLATE ascii_bin NULL AFTER model_version;

ALTER TABLE reviewer_restaurant_recommendation
    ADD COLUMN observed_p90_radius_km DOUBLE NULL AFTER search_radius_km;

ALTER TABLE reviewer_restaurant_recommendation
    ADD COLUMN local_p90_radius_km DOUBLE NULL AFTER observed_p90_radius_km;

ALTER TABLE reviewer_restaurant_recommendation
    ADD COLUMN travel_outlier_count INT UNSIGNED NULL AFTER local_p90_radius_km;

ALTER TABLE reviewer_restaurant_recommendation
    ADD COLUMN activity_cluster_count INT UNSIGNED NULL AFTER travel_outlier_count;

ALTER TABLE reviewer_restaurant_recommendation
    ADD COLUMN primary_cluster_business_count INT UNSIGNED NULL AFTER activity_cluster_count;
