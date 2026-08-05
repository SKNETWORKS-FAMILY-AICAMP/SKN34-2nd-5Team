CREATE TABLE IF NOT EXISTS business_review_supply (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    business_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    activity_year SMALLINT UNSIGNED NOT NULL,
    review_count BIGINT UNSIGNED NOT NULL,
    previous_year_review_count BIGINT UNSIGNED NULL,
    yoy_review_change BIGINT NULL,
    yoy_review_change_rate DOUBLE NULL,
    is_comparison_year TINYINT(1) NOT NULL,
    is_selection_year TINYINT(1) NOT NULL,
    calculation_method VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, business_id, activity_year),
    KEY idx_business_supply_year (model_version, activity_year),
    KEY idx_business_supply_decline (model_version, activity_year, yoy_review_change_rate),
    CONSTRAINT fk_business_supply_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version),
    CONSTRAINT chk_business_supply_counts CHECK (review_count >= 0),
    CONSTRAINT chk_business_supply_flags
        CHECK (is_comparison_year IN (0, 1) AND is_selection_year IN (0, 1))
) ENGINE=InnoDB;
