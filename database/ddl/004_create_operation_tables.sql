CREATE TABLE IF NOT EXISTS retention_playbooks (
    playbook_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    manager_decision VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    condition_text TEXT NOT NULL,
    signals_text TEXT NOT NULL,
    primary_action TEXT NOT NULL,
    channel VARCHAR(255) NOT NULL,
    needs_upgrade TEXT NOT NULL,
    success_criteria TEXT NOT NULL,
    display_order SMALLINT UNSIGNED NOT NULL,
    is_active TINYINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (playbook_id),
    UNIQUE KEY uq_retention_playbooks_manager_decision (manager_decision),
    CONSTRAINT chk_retention_playbooks_active CHECK (is_active IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retention_playbook_risk_actions (
    playbook_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    risk_type VARCHAR(64) NOT NULL,
    sub_strategy_text TEXT NOT NULL,
    display_order SMALLINT UNSIGNED NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (playbook_id, risk_type),
    CONSTRAINT fk_playbook_risk_actions_playbook
        FOREIGN KEY (playbook_id)
        REFERENCES retention_playbooks (playbook_id)
        ON DELETE CASCADE
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
