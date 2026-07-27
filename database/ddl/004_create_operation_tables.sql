CREATE TABLE IF NOT EXISTS retention_playbooks (
    playbook_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    manager_decision VARCHAR(64) NOT NULL,
    risk_type VARCHAR(64) NULL,
    title VARCHAR(255) NOT NULL,
    primary_action TEXT NOT NULL,
    channel VARCHAR(255) NULL,
    success_criteria TEXT NULL,
    is_active TINYINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (playbook_id),
    CONSTRAINT chk_retention_playbooks_active CHECK (is_active IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS operator_decisions (
    decision_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    manager_decision VARCHAR(64) NOT NULL,
    risk_type VARCHAR(64) NULL,
    model_judgment VARCHAR(32) NULL,
    decision_reason TEXT NULL,
    decision_owner VARCHAR(128) NULL,
    decided_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    playbook_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
    review_due_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (decision_id),
    CONSTRAINT fk_operator_decisions_prediction
        FOREIGN KEY (model_version, sample_id)
        REFERENCES model_predictions (model_version, sample_id),
    CONSTRAINT fk_operator_decisions_playbook
        FOREIGN KEY (playbook_id)
        REFERENCES retention_playbooks (playbook_id)
) ENGINE=InnoDB;
