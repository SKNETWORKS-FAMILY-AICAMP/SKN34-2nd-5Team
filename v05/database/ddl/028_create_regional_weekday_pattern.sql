-- Weekday distribution for the unified v05_05_dl culinary operating context.
-- ISO weekday uses 1=Monday through 7=Sunday.

CREATE TABLE IF NOT EXISTS regional_weekday_pattern (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    activity_year SMALLINT UNSIGNED NOT NULL,
    iso_weekday TINYINT UNSIGNED NOT NULL,
    review_count BIGINT UNSIGNED NOT NULL,
    active_reviewer_count BIGINT UNSIGNED NOT NULL,
    active_business_count BIGINT UNSIGNED NOT NULL,
    calculation_method VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, state, activity_year, iso_weekday),
    KEY idx_regional_weekday_year (model_version, activity_year),
    CONSTRAINT fk_regional_weekday_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version),
    CONSTRAINT chk_regional_weekday_day CHECK (iso_weekday BETWEEN 1 AND 7),
    CONSTRAINT chk_regional_weekday_counts
        CHECK (review_count >= 0 AND active_reviewer_count >= 0
               AND active_business_count >= 0)
) ENGINE=InnoDB;

-- First observed cohort entry for the current operating cohort.  This keeps
-- historical entry context separate from cohort_samples: v05_05_dl stores
-- predictions only for its 2018 Test cohort, while first entry can precede it.
CREATE TABLE IF NOT EXISTS reviewer_operating_entry (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    first_selection_year SMALLINT UNSIGNED NOT NULL,
    first_state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    first_city VARCHAR(128) NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id),
    KEY idx_reviewer_operating_entry_user (model_version, user_id),
    CONSTRAINT fk_reviewer_operating_entry_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id)
) ENGINE=InnoDB;
