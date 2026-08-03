-- 모든 issue_count가 0이어야 한다.

SELECT 'invalid_individual_scope' AS check_name, COUNT(*) AS issue_count
FROM retention_action_plans
WHERE plan_type = 'individual'
  AND (reviewer_user_id IS NULL OR sample_id IS NULL OR region_code IS NOT NULL);

SELECT 'invalid_regional_scope' AS check_name, COUNT(*) AS issue_count
FROM retention_action_plans
WHERE plan_type = 'regional'
  AND (region_code IS NULL OR reviewer_user_id IS NOT NULL OR sample_id IS NOT NULL);

SELECT 'individual_without_matching_sample' AS check_name, COUNT(*) AS issue_count
FROM retention_action_plans AS plan
LEFT JOIN cohort_samples AS sample
  ON sample.model_version = plan.model_version
 AND sample.sample_id = plan.sample_id
 AND sample.user_id = plan.reviewer_user_id
WHERE plan.plan_type = 'individual' AND sample.sample_id IS NULL;

SELECT 'plan_missing_actor' AS check_name, COUNT(*) AS issue_count
FROM retention_action_plans
WHERE created_by_subject = '' OR created_by_name = ''
   OR updated_by_subject = '' OR updated_by_name = '';

SELECT 'invalid_milestone_day' AS check_name, COUNT(*) AS issue_count
FROM retention_action_plan_milestones
WHERE day_offset NOT IN (30, 60, 90);

SELECT 'orphan_plan_children' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT channel.plan_id FROM retention_action_plan_channels AS channel
    LEFT JOIN retention_action_plans AS plan ON plan.plan_id = channel.plan_id
    WHERE plan.plan_id IS NULL
    UNION ALL
    SELECT business.plan_id FROM retention_action_plan_businesses AS business
    LEFT JOIN retention_action_plans AS plan ON plan.plan_id = business.plan_id
    WHERE plan.plan_id IS NULL
    UNION ALL
    SELECT milestone.plan_id FROM retention_action_plan_milestones AS milestone
    LEFT JOIN retention_action_plans AS plan ON plan.plan_id = milestone.plan_id
    WHERE plan.plan_id IS NULL
) AS orphan_rows;
