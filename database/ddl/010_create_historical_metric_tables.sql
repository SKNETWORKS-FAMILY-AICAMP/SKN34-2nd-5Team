-- v02/v03는 저장소에 모델 바이너리가 없고 Trust Center 비교 리포트만
-- 보존되어 있다. 모델 파일 SHA를 꾸며 넣지 않도록 NULL을 허용한다.
ALTER TABLE model_versions
    MODIFY model_sha256 CHAR(64)
        CHARACTER SET ascii COLLATE ascii_bin NULL;

-- v03 그룹 중요도는 반복 순열이 아니라 1회 그룹 제거 재학습 결과라
-- 원본 CSV의 표준편차가 NULL이다.
ALTER TABLE feature_group_importance
    MODIFY importance_std DOUBLE NULL;

CREATE TABLE IF NOT EXISTS model_binary_validation_metrics (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    split VARCHAR(64) NOT NULL,
    selection_year SMALLINT UNSIGNED NOT NULL,
    target_year SMALLINT UNSIGNED NOT NULL,
    train_selection_years VARCHAR(32) NULL,
    train_samples INT UNSIGNED NULL,
    validation_samples INT UNSIGNED NOT NULL,
    evaluation_policy VARCHAR(64) NOT NULL,
    threshold DOUBLE NOT NULL,
    accuracy DOUBLE NOT NULL,
    precision_score DOUBLE NOT NULL,
    recall_score DOUBLE NOT NULL,
    f1 DOUBLE NOT NULL,
    roc_auc DOUBLE NOT NULL,
    pr_auc DOUBLE NOT NULL,
    true_negative INT UNSIGNED NOT NULL,
    false_positive INT UNSIGNED NOT NULL,
    false_negative INT UNSIGNED NOT NULL,
    true_positive INT UNSIGNED NOT NULL,
    predicted_positive_rate DOUBLE NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, split),
    CONSTRAINT fk_model_binary_validation_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS model_binary_topk_metrics (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    split VARCHAR(64) NOT NULL,
    target_rate DECIMAL(6,5) NOT NULL,
    target_users INT UNSIGNED NOT NULL,
    captured_churn_users INT UNSIGNED NOT NULL,
    precision_at_k DOUBLE NOT NULL,
    recall_at_k DOUBLE NOT NULL,
    lift_at_k DOUBLE NOT NULL,
    minimum_risk_score DOUBLE NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, split, target_rate),
    CONSTRAINT fk_model_binary_topk_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version)
) ENGINE=InnoDB;
