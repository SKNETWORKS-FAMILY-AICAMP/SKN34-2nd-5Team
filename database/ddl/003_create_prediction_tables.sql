CREATE TABLE IF NOT EXISTS model_predictions (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    retained_score DOUBLE NOT NULL,
    weakened_score DOUBLE NOT NULL,
    stopped_score DOUBLE NOT NULL,
    priority_score DOUBLE NOT NULL,
    predicted_state TINYINT UNSIGNED NOT NULL,
    predicted_state_label VARCHAR(32) NOT NULL,
    priority_rank INT UNSIGNED NOT NULL,
    priority_top_percent DOUBLE NOT NULL,
    selected_for_crm TINYINT UNSIGNED NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, sample_id),
    UNIQUE KEY uq_model_predictions_rank (model_version, priority_rank),
    CONSTRAINT fk_model_predictions_sample
        FOREIGN KEY (model_version, sample_id)
        REFERENCES cohort_samples (model_version, sample_id),
    CONSTRAINT chk_model_predictions_state
        CHECK (predicted_state IN (0, 1, 2)),
    CONSTRAINT chk_model_predictions_crm
        CHECK (selected_for_crm IN (0, 1)),
    CONSTRAINT chk_model_predictions_rank CHECK (priority_rank > 0),
    CONSTRAINT chk_model_predictions_percent
        CHECK (priority_top_percent > 0 AND priority_top_percent <= 100)
) ENGINE=InnoDB;
