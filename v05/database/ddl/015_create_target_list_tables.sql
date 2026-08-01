-- v05 F-5: 대상 명단(target list) 서버 저장.
-- retention_decisions/retention_interactions와 동일하게 로그인 계정 테이블을
-- 복제하지 않고 subject 문자열만 저장한다. 기존 database/ DDL은 변경하지 않는다.

CREATE TABLE IF NOT EXISTS target_lists (
    list_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    decision VARCHAR(64) NOT NULL,
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    created_by_subject VARCHAR(128) NOT NULL,
    created_by_name VARCHAR(128) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (list_id),
    KEY idx_target_lists_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS target_list_members (
    list_id BIGINT UNSIGNED NOT NULL,
    reviewer_user_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    sample_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    added_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (list_id, reviewer_user_id),
    CONSTRAINT fk_target_list_members_list
        FOREIGN KEY (list_id)
        REFERENCES target_lists (list_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_target_list_members_prediction
        FOREIGN KEY (model_version, sample_id)
        REFERENCES model_predictions (model_version, sample_id)
) ENGINE=InnoDB;
