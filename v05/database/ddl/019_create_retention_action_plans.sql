-- v05 개인 특별 관리안·지역 활성화 캠페인 저장 계약.
-- 기존 database/와 인증 DB는 변경하지 않는다.

CREATE TABLE IF NOT EXISTS retention_action_plans (
    plan_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    plan_type VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    reviewer_user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
    region_code VARCHAR(32) NULL,
    target_list_id BIGINT UNSIGNED NULL,
    manager_decision VARCHAR(64) NULL,
    action_type VARCHAR(128) NOT NULL,
    message_title VARCHAR(255) NULL,
    message_body TEXT NULL,
    plan_status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'draft',
    created_by_subject VARCHAR(128) NOT NULL,
    created_by_name VARCHAR(128) NOT NULL,
    updated_by_subject VARCHAR(128) NOT NULL,
    updated_by_name VARCHAR(128) NOT NULL,
    lock_version INT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (plan_id),
    KEY idx_action_plans_reviewer (reviewer_user_id, updated_at),
    KEY idx_action_plans_region (region_code, updated_at),
    KEY idx_action_plans_target_list (target_list_id),
    CONSTRAINT fk_action_plans_target_list
        FOREIGN KEY (target_list_id) REFERENCES target_lists (list_id)
        ON DELETE SET NULL,
    CONSTRAINT chk_action_plans_type CHECK (plan_type IN ('individual', 'regional')),
    CONSTRAINT chk_action_plans_status CHECK (plan_status IN ('draft', 'saved', 'archived')),
    CONSTRAINT chk_action_plans_scope CHECK (
        (plan_type = 'individual' AND reviewer_user_id IS NOT NULL AND sample_id IS NOT NULL)
        OR (plan_type = 'regional' AND region_code IS NOT NULL)
    )
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retention_action_plan_channels (
    plan_id BIGINT UNSIGNED NOT NULL,
    channel VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    PRIMARY KEY (plan_id, channel),
    CONSTRAINT fk_action_plan_channels_plan
        FOREIGN KEY (plan_id) REFERENCES retention_action_plans (plan_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_action_plan_channel CHECK (
        channel IN ('app', 'email', 'push', 'phone', 'operator')
    )
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retention_action_plan_businesses (
    plan_id BIGINT UNSIGNED NOT NULL,
    business_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    display_order SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (plan_id, business_id),
    KEY idx_action_plan_business_order (plan_id, display_order),
    CONSTRAINT fk_action_plan_businesses_plan
        FOREIGN KEY (plan_id) REFERENCES retention_action_plans (plan_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retention_action_plan_milestones (
    plan_id BIGINT UNSIGNED NOT NULL,
    day_offset SMALLINT UNSIGNED NOT NULL,
    metric_code VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    metric_label VARCHAR(128) NOT NULL,
    observation_note VARCHAR(500) NULL,
    PRIMARY KEY (plan_id, day_offset, metric_code),
    CONSTRAINT fk_action_plan_milestones_plan
        FOREIGN KEY (plan_id) REFERENCES retention_action_plans (plan_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_action_plan_day CHECK (day_offset IN (30, 60, 90))
) ENGINE=InnoDB;
