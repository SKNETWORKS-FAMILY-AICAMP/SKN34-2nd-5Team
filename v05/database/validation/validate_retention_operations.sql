-- 모든 issue_count가 0이어야 한다.

SELECT 'decision_without_matching_reviewer' AS check_name, COUNT(*) AS issue_count
FROM retention_decisions AS decision_row
LEFT JOIN cohort_samples AS sample
  ON sample.model_version = decision_row.model_version
 AND sample.sample_id = decision_row.sample_id
 AND sample.user_id = decision_row.reviewer_user_id
WHERE sample.sample_id IS NULL;

SELECT 'interaction_without_matching_reviewer' AS check_name, COUNT(*) AS issue_count
FROM retention_interactions AS interaction_row
LEFT JOIN cohort_samples AS sample
  ON sample.model_version = interaction_row.model_version
 AND sample.sample_id = interaction_row.sample_id
 AND sample.user_id = interaction_row.reviewer_user_id
WHERE sample.sample_id IS NULL;

SELECT 'decision_missing_actor' AS check_name, COUNT(*) AS issue_count
FROM retention_decisions
WHERE updated_by_subject = '' OR updated_by_name = '';

SELECT 'history_missing_actor' AS check_name, COUNT(*) AS issue_count
FROM retention_decision_history
WHERE actor_subject = '' OR actor_name = '';

SELECT 'history_invalid_transition' AS check_name, COUNT(*) AS issue_count
FROM retention_decision_history
WHERE (action_type = 'created' AND (from_decision IS NOT NULL OR to_decision IS NULL))
   OR (action_type = 'deleted' AND (from_decision IS NULL OR to_decision IS NOT NULL))
   OR (action_type = 'updated' AND (from_decision IS NULL OR to_decision IS NULL));
