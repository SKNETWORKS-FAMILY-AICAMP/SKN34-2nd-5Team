-- v05 운영 데이터. 기존 database/ DDL과 분석 테이블은 변경하지 않는다.
-- 로그인 시스템은 별도 팀 작업이므로 계정 테이블을 복제하거나 FK로 결합하지 않고,
-- 인증 공급자가 주는 안정적인 subject 문자열을 저장한다.

CREATE TABLE IF NOT EXISTS retention_decisions (
    reviewer_user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    manager_decision VARCHAR(64) NOT NULL,
    note TEXT NULL,
    assignee_subject VARCHAR(128) NULL,
    snooze_until DATETIME(6) NULL,
    risk_type VARCHAR(64) NULL,
    model_judgment VARCHAR(32) NULL,
    updated_by_subject VARCHAR(128) NOT NULL,
    updated_by_name VARCHAR(128) NOT NULL,
    lock_version INT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (reviewer_user_id),
    KEY idx_retention_decisions_sample (model_version, sample_id),
    KEY idx_retention_decisions_assignee (assignee_subject),
    KEY idx_retention_decisions_snooze (snooze_until),
    CONSTRAINT fk_retention_decisions_prediction
        FOREIGN KEY (model_version, sample_id)
        REFERENCES model_predictions (model_version, sample_id),
    CONSTRAINT chk_retention_decisions_value CHECK (
        manager_decision IN (
            '리뷰 다시 시작 유도',
            '리뷰 활동 늘리기',
            '변화 지켜보기',
            '이번엔 제외'
        )
    )
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retention_decision_history (
    history_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    reviewer_user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    action_type VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    from_decision VARCHAR(64) NULL,
    to_decision VARCHAR(64) NULL,
    from_note TEXT NULL,
    to_note TEXT NULL,
    from_assignee_subject VARCHAR(128) NULL,
    to_assignee_subject VARCHAR(128) NULL,
    from_snooze_until DATETIME(6) NULL,
    to_snooze_until DATETIME(6) NULL,
    actor_subject VARCHAR(128) NOT NULL,
    actor_name VARCHAR(128) NOT NULL,
    changed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (history_id),
    KEY idx_retention_history_reviewer (reviewer_user_id, changed_at),
    KEY idx_retention_history_actor (actor_subject, changed_at),
    CONSTRAINT chk_retention_history_action CHECK (
        action_type IN ('created', 'updated', 'deleted')
    )
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retention_interactions (
    interaction_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    reviewer_user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    channel VARCHAR(32) NOT NULL,
    contacted_at DATETIME(6) NOT NULL,
    note TEXT NULL,
    actor_subject VARCHAR(128) NOT NULL,
    actor_name VARCHAR(128) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (interaction_id),
    KEY idx_retention_interactions_reviewer (reviewer_user_id, contacted_at),
    KEY idx_retention_interactions_actor (actor_subject, contacted_at),
    CONSTRAINT fk_retention_interactions_prediction
        FOREIGN KEY (model_version, sample_id)
        REFERENCES model_predictions (model_version, sample_id),
    CONSTRAINT chk_retention_interactions_channel CHECK (
        channel IN ('app', 'email', 'push', 'phone', 'other')
    )
) ENGINE=InnoDB;
