CREATE TABLE IF NOT EXISTS reviewer_region (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    top_city VARCHAR(128) NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id),
    KEY idx_reviewer_region_state (model_version, state),
    KEY idx_reviewer_region_city (model_version, state, top_city),
    CONSTRAINT fk_reviewer_region_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id),
    CONSTRAINT chk_reviewer_region_state
        CHECK (CHAR_LENGTH(state) BETWEEN 2 AND 3)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reviewer_monthly_activity (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    `year_month` CHAR(7) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    review_count INT UNSIGNED NOT NULL,
    unique_business_count INT UNSIGNED NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id, `year_month`),
    KEY idx_reviewer_monthly_period (model_version, `year_month`),
    CONSTRAINT fk_reviewer_monthly_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id),
    CONSTRAINT chk_reviewer_monthly_period
        CHECK (
            `year_month` REGEXP '^[0-9]{4}-(0[1-9]|1[0-2])$'
        ),
    CONSTRAINT chk_reviewer_monthly_counts
        CHECK (
            review_count > 0
            AND unique_business_count > 0
            AND unique_business_count <= review_count
        )
) ENGINE=InnoDB;
