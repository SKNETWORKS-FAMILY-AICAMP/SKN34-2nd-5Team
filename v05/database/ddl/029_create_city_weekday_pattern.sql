-- City-level weekday distribution for the unified v05_05_dl culinary context.
-- ISO weekday uses 1=Monday through 7=Sunday.

CREATE TABLE IF NOT EXISTS city_weekday_pattern (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    city_key VARCHAR(128) NOT NULL,
    city VARCHAR(128) NOT NULL,
    activity_year SMALLINT UNSIGNED NOT NULL,
    iso_weekday TINYINT UNSIGNED NOT NULL,
    review_count BIGINT UNSIGNED NOT NULL,
    active_reviewer_count BIGINT UNSIGNED NOT NULL,
    active_business_count BIGINT UNSIGNED NOT NULL,
    calculation_method VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, state, city_key, activity_year, iso_weekday),
    KEY idx_city_weekday_year (model_version, activity_year, state),
    CONSTRAINT fk_city_weekday_model
        FOREIGN KEY (model_version) REFERENCES model_versions (model_version),
    CONSTRAINT chk_city_weekday_day CHECK (iso_weekday BETWEEN 1 AND 7),
    CONSTRAINT chk_city_weekday_counts
        CHECK (review_count >= 0 AND active_reviewer_count >= 0
               AND active_business_count >= 0)
) ENGINE=InnoDB;
