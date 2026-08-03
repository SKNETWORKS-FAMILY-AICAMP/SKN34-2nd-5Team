-- v05 city operating context.
-- Review and apply manually to the existing yelp_data database.
-- Existing regional/model tables are not altered.

CREATE TABLE IF NOT EXISTS city_review_supply (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    city_key VARCHAR(128) NOT NULL,
    city VARCHAR(128) NOT NULL,
    activity_year SMALLINT UNSIGNED NOT NULL,
    center_latitude DOUBLE NOT NULL,
    center_longitude DOUBLE NOT NULL,
    p90_radius_km DOUBLE NOT NULL,
    review_count BIGINT UNSIGNED NOT NULL,
    active_reviewer_count BIGINT UNSIGNED NOT NULL,
    active_business_count BIGINT UNSIGNED NOT NULL,
    previous_year_review_count BIGINT UNSIGNED NULL,
    yoy_review_change BIGINT NULL,
    yoy_review_change_rate DOUBLE NULL,
    minimum_sample_met TINYINT(1) NOT NULL,
    is_comparison_year TINYINT(1) NOT NULL,
    is_selection_year TINYINT(1) NOT NULL,
    calculation_method VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, state, city_key, activity_year),
    KEY idx_city_supply_year (model_version, activity_year),
    KEY idx_city_supply_priority
        (model_version, activity_year, minimum_sample_met, yoy_review_change_rate),
    CONSTRAINT fk_city_supply_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version),
    CONSTRAINT chk_city_supply_counts
        CHECK (review_count > 0 AND active_reviewer_count > 0
               AND active_business_count > 0),
    CONSTRAINT chk_city_supply_coordinates
        CHECK (center_latitude BETWEEN -90 AND 90
               AND center_longitude BETWEEN -180 AND 180
               AND p90_radius_km >= 0),
    CONSTRAINT chk_city_supply_flags
        CHECK (minimum_sample_met IN (0, 1)
               AND is_comparison_year IN (0, 1)
               AND is_selection_year IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS city_newcomer (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    selection_year SMALLINT UNSIGNED NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    city_key VARCHAR(128) NOT NULL,
    city VARCHAR(128) NOT NULL,
    new_power_reviewers INT UNSIGNED NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, selection_year, state, city_key),
    KEY idx_city_newcomer_location
        (model_version, state, city_key, selection_year),
    CONSTRAINT fk_city_newcomer_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version),
    CONSTRAINT chk_city_newcomer_count CHECK (new_power_reviewers > 0)
) ENGINE=InnoDB;

