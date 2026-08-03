-- v05 재검토 업무 알림과 권역 운영자 범위.
-- auth_service 계정 테이블은 팀원 소유이므로 FK로 결합하지 않고 안정적인 subject만 저장한다.

CREATE TABLE IF NOT EXISTS retention_operator_scopes (
    auth_subject VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    operator_label VARCHAR(128) NOT NULL,
    region_code VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_by_subject VARCHAR(128) NOT NULL,
    created_by_name VARCHAR(128) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (auth_subject, region_code),
    KEY idx_retention_operator_scope_region (region_code, is_active),
    CONSTRAINT chk_retention_operator_scope_active CHECK (is_active IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retention_review_alerts (
    alert_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    reviewer_user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    due_at DATETIME(6) NOT NULL,
    status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'open',
    assigned_subject VARCHAR(128) NULL,
    assigned_name VARCHAR(128) NULL,
    resolution_note TEXT NULL,
    resolved_by_subject VARCHAR(128) NULL,
    resolved_by_name VARCHAR(128) NULL,
    resolved_at DATETIME(6) NULL,
    created_by_subject VARCHAR(128) NOT NULL,
    created_by_name VARCHAR(128) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (alert_id),
    UNIQUE KEY uq_retention_review_alert_due (reviewer_user_id, model_version, due_at),
    KEY idx_retention_review_alert_status_due (status, due_at),
    KEY idx_retention_review_alert_assignee (assigned_subject, status, due_at),
    KEY idx_retention_review_alert_sample (model_version, sample_id),
    CONSTRAINT fk_retention_review_alert_prediction
        FOREIGN KEY (model_version, sample_id)
        REFERENCES model_predictions (model_version, sample_id),
    CONSTRAINT chk_retention_review_alert_status CHECK (
        status IN ('open', 'completed', 'dismissed')
    ),
    CONSTRAINT chk_retention_review_alert_resolution CHECK (
        (status = 'open' AND resolved_at IS NULL)
        OR (status IN ('completed', 'dismissed') AND resolved_at IS NOT NULL)
    )
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retention_review_alert_history (
    history_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    alert_id BIGINT UNSIGNED NOT NULL,
    action_type VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    from_status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NULL,
    to_status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    note TEXT NULL,
    actor_subject VARCHAR(128) NOT NULL,
    actor_name VARCHAR(128) NOT NULL,
    changed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (history_id),
    KEY idx_retention_review_alert_history_alert (alert_id, changed_at),
    KEY idx_retention_review_alert_history_actor (actor_subject, changed_at),
    CONSTRAINT fk_retention_review_alert_history_alert
        FOREIGN KEY (alert_id) REFERENCES retention_review_alerts (alert_id),
    CONSTRAINT chk_retention_review_alert_history_action CHECK (
        action_type IN ('created', 'completed', 'dismissed', 'reopened')
    )
) ENGINE=InnoDB;

-- 기존 관리자 판단의 재검토 시점을 최초 알림으로 이관한다.
INSERT IGNORE INTO retention_review_alerts (
    reviewer_user_id, model_version, sample_id, due_at, status,
    assigned_subject, assigned_name,
    created_by_subject, created_by_name, created_at, updated_at
)
SELECT
    decision_row.reviewer_user_id,
    decision_row.model_version,
    decision_row.sample_id,
    decision_row.snooze_until,
    'open',
    decision_row.assignee_subject,
    CASE
        WHEN decision_row.assignee_subject = decision_row.updated_by_subject
            THEN decision_row.updated_by_name
        ELSE NULL
    END,
    decision_row.updated_by_subject,
    decision_row.updated_by_name,
    decision_row.created_at,
    decision_row.updated_at
FROM retention_decisions AS decision_row
WHERE decision_row.snooze_until IS NOT NULL;

INSERT INTO retention_review_alert_history (
    alert_id, action_type, from_status, to_status,
    note, actor_subject, actor_name, changed_at
)
SELECT
    alert_row.alert_id,
    'created',
    NULL,
    'open',
    '기존 재검토 시점 백필',
    alert_row.created_by_subject,
    alert_row.created_by_name,
    alert_row.created_at
FROM retention_review_alerts AS alert_row
LEFT JOIN retention_review_alert_history AS history_row
  ON history_row.alert_id = alert_row.alert_id
WHERE history_row.history_id IS NULL;
