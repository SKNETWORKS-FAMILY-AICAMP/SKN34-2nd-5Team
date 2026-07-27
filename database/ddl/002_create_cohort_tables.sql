CREATE TABLE IF NOT EXISTS cohort_samples (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    comparison_year SMALLINT UNSIGNED NOT NULL,
    selection_year SMALLINT UNSIGNED NOT NULL,
    target_year SMALLINT UNSIGNED NOT NULL,
    prior_activity_available TINYINT UNSIGNED NOT NULL,
    scope VARCHAR(128) NOT NULL,
    split_v04 VARCHAR(32) NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id),
    CONSTRAINT fk_cohort_samples_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version),
    CONSTRAINT chk_cohort_samples_prior
        CHECK (prior_activity_available IN (0, 1)),
    CONSTRAINT chk_cohort_samples_time
        CHECK (
            comparison_year + 1 = selection_year
            AND selection_year + 1 = target_year
        )
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reviewer_features (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    baseline_review_count INT NOT NULL,
    baseline_active_months INT NOT NULL,
    baseline_reviews_per_active_month DOUBLE NULL,
    recent_review_count INT NOT NULL,
    recent_active_months INT NOT NULL,
    recent_reviews_per_active_month DOUBLE NULL,
    review_count_diff INT NULL,
    review_count_ratio DOUBLE NULL,
    review_count_decline_rate DOUBLE NULL,
    active_month_diff INT NULL,
    active_month_ratio DOUBLE NULL,
    active_month_decline_rate DOUBLE NULL,
    reviews_per_active_month_diff DOUBLE NULL,
    reviews_per_active_month_ratio DOUBLE NULL,
    reviews_per_active_month_decline_rate DOUBLE NULL,
    baseline_mean_interval_days DOUBLE NULL,
    baseline_median_interval_days DOUBLE NULL,
    baseline_max_interval_days DOUBLE NULL,
    baseline_recency_days DOUBLE NULL,
    recent_mean_interval_days DOUBLE NULL,
    recent_median_interval_days DOUBLE NULL,
    recent_max_interval_days DOUBLE NULL,
    recent_recency_days DOUBLE NULL,
    recent_interval_available TINYINT UNSIGNED NOT NULL,
    mean_interval_increase_days DOUBLE NULL,
    median_interval_increase_days DOUBLE NULL,
    max_interval_increase_days DOUBLE NULL,
    recency_increase_days DOUBLE NULL,
    baseline_unique_business_count BIGINT NOT NULL,
    recent_unique_business_count BIGINT NOT NULL,
    recent_revisited_business_count BIGINT NOT NULL,
    recent_new_vs_baseline_count BIGINT NOT NULL,
    unique_business_count_diff BIGINT NULL,
    unique_business_ratio DOUBLE NULL,
    unique_business_decline_rate DOUBLE NULL,
    recent_revisit_rate DOUBLE NULL,
    recent_new_vs_baseline_rate DOUBLE NULL,
    baseline_new_business_count INT NOT NULL,
    recent_new_business_count INT NOT NULL,
    baseline_new_business_rate DOUBLE NULL,
    recent_new_business_rate DOUBLE NULL,
    new_business_count_diff INT NULL,
    new_business_rate_decline DOUBLE NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id),
    CONSTRAINT fk_reviewer_features_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id),
    CONSTRAINT chk_reviewer_features_interval_available
        CHECK (recent_interval_available IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS validation_outcomes (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    target_review_count INT UNSIGNED NOT NULL,
    target_active_months TINYINT UNSIGNED NOT NULL,
    retention_state TINYINT UNSIGNED NOT NULL,
    churn TINYINT UNSIGNED NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id),
    CONSTRAINT fk_validation_outcomes_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id),
    CONSTRAINT chk_validation_outcomes_state
        CHECK (retention_state IN (0, 1, 2)),
    CONSTRAINT chk_validation_outcomes_churn
        CHECK (churn IN (0, 1))
) ENGINE=InnoDB;
