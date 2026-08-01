-- Reviewer P90 activity radius per period, from
-- data/processed/spatial/reviewer_spatial_summaries_v04.parquet
-- (v05/pipeline/build_spatial_v04.py). Powers A-8 (Reviewer 360 radius
-- tool) and A-7 (regional travel-range tab) — see docs/ui/V05_WORK_SPEC.md
-- G-3/G-5. period_type is 'comparison' (baseline year) or 'selection'
-- (target year); comparison rows only exist for reviewers with prior
-- activity, so this table has fewer rows per model_version than
-- cohort_samples (11,374 for v04's 6,533 selection + 4,841 comparison).
--
-- calculation_method and earth_radius_km from the source parquet are
-- pipeline metadata (constant across all rows, "median_center_haversine_p90"
-- / 6371.0 for v04) — not stored per-row here, documented in the pipeline
-- script instead.
CREATE TABLE IF NOT EXISTS reviewer_spatial_summary (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    period_type VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    activity_year SMALLINT UNSIGNED NOT NULL,
    center_latitude DOUBLE NOT NULL,
    center_longitude DOUBLE NOT NULL,
    spatial_business_count INT UNSIGNED NOT NULL,
    activity_review_count INT UNSIGNED NOT NULL,
    median_radius_km DOUBLE NOT NULL,
    mean_radius_km DOUBLE NOT NULL,
    p90_radius_km DOUBLE NOT NULL,
    max_radius_km DOUBLE NOT NULL,
    radius_available TINYINT(1) NOT NULL,
    -- Only populated on period_type='selection' rows (change vs. that
    -- reviewer's own comparison-year row, when one exists).
    radius_change_km DOUBLE NULL,
    radius_change_rate DOUBLE NULL,
    center_shift_km DOUBLE NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id, period_type),
    KEY idx_reviewer_spatial_period (model_version, period_type),
    CONSTRAINT fk_reviewer_spatial_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id),
    CONSTRAINT chk_reviewer_spatial_period_type
        CHECK (period_type IN ('comparison', 'selection'))
) ENGINE=InnoDB;
