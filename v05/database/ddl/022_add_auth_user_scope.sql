-- v05 관리자 생성 계정과 담당 권역 범위.
-- auth_service/database.py가 로컬 실행 시 동일 컬럼을 호환 마이그레이션한다.
-- 이 파일은 팀 DB 반영 시 사용할 명시적 MySQL 변경 이력이다.

ALTER TABLE auth_users
    ADD COLUMN region_code VARCHAR(16) NULL AFTER access_role,
    ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0 AFTER region_code,
    ADD COLUMN last_login_at DATETIME(6) NULL AFTER approved_at,
    ADD KEY ix_auth_users_region_code (region_code),
    ADD CONSTRAINT chk_auth_users_must_change_password
        CHECK (must_change_password IN (0, 1)),
    ADD CONSTRAINT chk_auth_users_role_region
        CHECK (
            (access_role = 'OPERATOR' AND region_code IS NOT NULL)
            OR access_role IN ('ADMIN', 'VIEWER')
            OR access_role IS NULL
        );

-- 기존 승인 운영자는 담당 권역 확정 전까지 조회 전용으로 보호한다.
UPDATE auth_users
SET access_role = 'VIEWER', region_code = NULL
WHERE access_role = 'OPERATOR' AND region_code IS NULL;

