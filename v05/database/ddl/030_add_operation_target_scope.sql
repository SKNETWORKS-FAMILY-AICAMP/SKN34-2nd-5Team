-- Persist the geographic scope selected for regional target lists and plans.
-- Existing regional plans are preserved as state-wide plans.

ALTER TABLE target_lists
    ADD COLUMN target_scope VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER model_version,
    ADD COLUMN region_code VARCHAR(32) NULL AFTER target_scope,
    ADD COLUMN city_key VARCHAR(128) NULL AFTER region_code,
    ADD COLUMN city_name VARCHAR(128) NULL AFTER city_key,
    ADD KEY idx_target_lists_geo (target_scope, region_code, city_key, created_at);

ALTER TABLE retention_action_plans
    DROP CHECK chk_action_plans_scope;

ALTER TABLE retention_action_plans
    ADD COLUMN target_scope VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER region_code,
    ADD COLUMN city_key VARCHAR(128) NULL AFTER target_scope,
    ADD COLUMN city_name VARCHAR(128) NULL AFTER city_key;

UPDATE retention_action_plans
SET target_scope = 'region'
WHERE plan_type = 'regional' AND target_scope IS NULL;

ALTER TABLE retention_action_plans
    ADD KEY idx_action_plans_geo (target_scope, region_code, city_key, updated_at),
    ADD CONSTRAINT chk_action_plans_scope CHECK (
        (plan_type = 'individual'
         AND reviewer_user_id IS NOT NULL AND sample_id IS NOT NULL
         AND target_scope IS NULL AND city_key IS NULL AND city_name IS NULL)
        OR
        (plan_type = 'regional' AND region_code IS NOT NULL AND (
            (target_scope = 'region' AND city_key IS NULL AND city_name IS NULL)
            OR
            (target_scope = 'city' AND city_key IS NOT NULL AND city_name IS NOT NULL)
        ))
    );
