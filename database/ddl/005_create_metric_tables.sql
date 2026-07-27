CREATE TABLE IF NOT EXISTS model_validation_metrics (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    record_type VARCHAR(32) NOT NULL,
    split VARCHAR(64) NOT NULL,
    train_selection_years VARCHAR(32) NULL,
    validation_selection_year SMALLINT UNSIGNED NULL,
    train_samples INT UNSIGNED NULL,
    validation_samples INT UNSIGNED NULL,
    accuracy DOUBLE NOT NULL,
    balanced_accuracy DOUBLE NOT NULL,
    macro_precision DOUBLE NOT NULL,
    macro_recall DOUBLE NOT NULL,
    macro_f1 DOUBLE NOT NULL,
    weighted_f1 DOUBLE NOT NULL,
    macro_pr_auc DOUBLE NOT NULL,
    macro_ovr_roc_auc DOUBLE NOT NULL,
    retained_precision DOUBLE NOT NULL,
    retained_recall DOUBLE NOT NULL,
    retained_f1 DOUBLE NOT NULL,
    retained_support DOUBLE NOT NULL,
    retained_pr_auc DOUBLE NOT NULL,
    retained_roc_auc DOUBLE NOT NULL,
    weakened_precision DOUBLE NOT NULL,
    weakened_recall DOUBLE NOT NULL,
    weakened_f1 DOUBLE NOT NULL,
    weakened_support DOUBLE NOT NULL,
    weakened_pr_auc DOUBLE NOT NULL,
    weakened_roc_auc DOUBLE NOT NULL,
    stopped_precision DOUBLE NOT NULL,
    stopped_recall DOUBLE NOT NULL,
    stopped_f1 DOUBLE NOT NULL,
    stopped_support DOUBLE NOT NULL,
    stopped_pr_auc DOUBLE NOT NULL,
    stopped_roc_auc DOUBLE NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, record_type, split),
    CONSTRAINT fk_model_validation_metrics_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS model_topk_metrics (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    split VARCHAR(64) NOT NULL,
    ranking VARCHAR(32) NOT NULL,
    target_rate DECIMAL(6,5) NOT NULL,
    target_users INT UNSIGNED NOT NULL,
    status_loss_captured INT UNSIGNED NOT NULL,
    status_loss_precision DOUBLE NOT NULL,
    status_loss_recall DOUBLE NOT NULL,
    status_loss_lift DOUBLE NOT NULL,
    stopped_captured INT UNSIGNED NOT NULL,
    stopped_recall DOUBLE NOT NULL,
    weakened_captured INT UNSIGNED NOT NULL,
    weakened_recall DOUBLE NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, split, ranking, target_rate),
    CONSTRAINT fk_model_topk_metrics_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS model_confusion_matrix (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    split VARCHAR(64) NOT NULL,
    actual_state VARCHAR(32) NOT NULL,
    predicted_state VARCHAR(32) NOT NULL,
    users INT UNSIGNED NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, split, actual_state, predicted_state),
    CONSTRAINT fk_model_confusion_matrix_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS feature_importance (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    split VARCHAR(64) NOT NULL,
    feature VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    rank_no SMALLINT UNSIGNED NOT NULL,
    feature_group VARCHAR(64) NOT NULL,
    feature_group_label VARCHAR(64) NOT NULL,
    importance_mean DOUBLE NOT NULL,
    importance_std DOUBLE NOT NULL,
    importance_share_pct DOUBLE NOT NULL,
    baseline_pr_auc DOUBLE NOT NULL,
    metric VARCHAR(64) NOT NULL,
    method VARCHAR(64) NOT NULL,
    repeats SMALLINT UNSIGNED NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, split, feature),
    CONSTRAINT fk_feature_importance_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS feature_group_importance (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    split VARCHAR(64) NOT NULL,
    feature_group VARCHAR(64) NOT NULL,
    feature_count SMALLINT UNSIGNED NOT NULL,
    rank_no SMALLINT UNSIGNED NOT NULL,
    feature_group_label VARCHAR(64) NOT NULL,
    importance_mean DOUBLE NOT NULL,
    importance_std DOUBLE NOT NULL,
    baseline_pr_auc DOUBLE NOT NULL,
    metric VARCHAR(64) NOT NULL,
    method VARCHAR(64) NOT NULL,
    repeats SMALLINT UNSIGNED NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, split, feature_group),
    CONSTRAINT fk_feature_group_importance_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version)
) ENGINE=InnoDB;
