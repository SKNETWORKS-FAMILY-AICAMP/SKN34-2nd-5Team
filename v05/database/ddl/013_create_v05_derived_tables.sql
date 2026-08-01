-- v05 derived-data staging schema.
-- Review and apply manually to the existing yelp_data database.

CREATE TABLE IF NOT EXISTS reviewer_restaurant_recommendation (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    selection_year SMALLINT UNSIGNED NOT NULL,
    business_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    city VARCHAR(128) NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    distance_km DOUBLE NOT NULL,
    matched_categories VARCHAR(1024) NOT NULL,
    primary_category VARCHAR(128) NOT NULL,
    category_match_score DOUBLE NOT NULL,
    stars DOUBLE NOT NULL,
    review_count INT UNSIGNED NOT NULL,
    recommendation_rank TINYINT UNSIGNED NOT NULL,
    radius_stage VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    search_radius_km DOUBLE NOT NULL,
    reason VARCHAR(255) NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id, recommendation_rank),
    UNIQUE KEY uq_reviewer_recommendation_business
        (model_version, sample_id, business_id),
    KEY idx_reviewer_recommendation_user (model_version, user_id),
    CONSTRAINT fk_reviewer_recommendation_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id),
    CONSTRAINT chk_reviewer_recommendation_rank
        CHECK (recommendation_rank BETWEEN 1 AND 3),
    CONSTRAINT chk_reviewer_recommendation_distance
        CHECK (distance_km >= 0 AND search_radius_km > 0 AND search_radius_km <= 50),
    CONSTRAINT chk_reviewer_recommendation_quality
        CHECK (stars >= 3.5 AND stars <= 5 AND review_count >= 10),
    CONSTRAINT chk_reviewer_recommendation_stage
        CHECK (radius_stage IN ('personal_p90', 'expanded_1_5x', 'fallback_50km'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reviewer_region_history (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    comparison_year SMALLINT UNSIGNED NOT NULL,
    selection_year SMALLINT UNSIGNED NOT NULL,
    baseline_review_count INT UNSIGNED NOT NULL,
    recent_review_count INT UNSIGNED NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    top_city VARCHAR(128) NULL,
    mapping_method VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id),
    KEY idx_region_history_year_state (model_version, selection_year, state),
    KEY idx_region_history_user (model_version, user_id, selection_year),
    CONSTRAINT fk_region_history_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id),
    CONSTRAINT chk_region_history_time
        CHECK (comparison_year + 1 = selection_year),
    CONSTRAINT chk_region_history_state
        CHECK (CHAR_LENGTH(state) BETWEEN 2 AND 3)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS regional_newcomer (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    selection_year SMALLINT UNSIGNED NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    new_power_reviewers INT UNSIGNED NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, selection_year, state),
    CONSTRAINT fk_regional_newcomer_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version),
    CONSTRAINT chk_regional_newcomer_count CHECK (new_power_reviewers > 0),
    CONSTRAINT chk_regional_newcomer_state
        CHECK (CHAR_LENGTH(state) BETWEEN 2 AND 3)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS regional_review_supply (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    activity_year SMALLINT UNSIGNED NOT NULL,
    review_count BIGINT UNSIGNED NOT NULL,
    active_reviewer_count BIGINT UNSIGNED NOT NULL,
    active_business_count BIGINT UNSIGNED NOT NULL,
    previous_year_review_count BIGINT UNSIGNED NULL,
    yoy_review_change BIGINT NULL,
    yoy_review_change_rate DOUBLE NULL,
    is_comparison_year TINYINT(1) NOT NULL,
    is_selection_year TINYINT(1) NOT NULL,
    calculation_method VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, state, activity_year),
    KEY idx_review_supply_year (model_version, activity_year),
    CONSTRAINT fk_review_supply_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version),
    CONSTRAINT chk_review_supply_counts
        CHECK (review_count > 0 AND active_reviewer_count > 0 AND active_business_count > 0),
    CONSTRAINT chk_review_supply_flags
        CHECK (is_comparison_year IN (0, 1) AND is_selection_year IN (0, 1))
) ENGINE=InnoDB;
