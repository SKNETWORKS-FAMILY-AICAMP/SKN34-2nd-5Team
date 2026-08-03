-- 모든 issue_count가 0이어야 한다.

SELECT 'alert_without_matching_reviewer' AS check_name, COUNT(*) AS issue_count
FROM retention_review_alerts AS alert_row
LEFT JOIN cohort_samples AS sample
  ON sample.model_version = alert_row.model_version
 AND sample.sample_id = alert_row.sample_id
 AND sample.user_id = alert_row.reviewer_user_id
WHERE sample.sample_id IS NULL;

SELECT 'alert_invalid_resolution_state' AS check_name, COUNT(*) AS issue_count
FROM retention_review_alerts
WHERE (status = 'open' AND resolved_at IS NOT NULL)
   OR (status IN ('completed', 'dismissed') AND resolved_at IS NULL);

SELECT 'alert_missing_actor' AS check_name, COUNT(*) AS issue_count
FROM retention_review_alerts
WHERE created_by_subject = '' OR created_by_name = '';

SELECT 'alert_history_missing_actor' AS check_name, COUNT(*) AS issue_count
FROM retention_review_alert_history
WHERE actor_subject = '' OR actor_name = '';

SELECT 'alert_without_created_history' AS check_name, COUNT(*) AS issue_count
FROM retention_review_alerts AS alert_row
LEFT JOIN retention_review_alert_history AS history_row
  ON history_row.alert_id = alert_row.alert_id
 AND history_row.action_type = 'created'
WHERE history_row.history_id IS NULL;

SELECT 'scope_invalid_region' AS check_name, COUNT(*) AS issue_count
FROM retention_operator_scopes AS scope_row
LEFT JOIN (
    SELECT DISTINCT state FROM reviewer_region WHERE model_version = 'v04'
) AS known_region
  ON known_region.state = scope_row.region_code
WHERE scope_row.is_active = 1 AND known_region.state IS NULL;

SELECT 'snooze_without_alert' AS check_name, COUNT(*) AS issue_count
FROM retention_decisions AS decision_row
LEFT JOIN retention_review_alerts AS alert_row
  ON alert_row.reviewer_user_id = decision_row.reviewer_user_id
 AND alert_row.model_version = decision_row.model_version
 AND alert_row.due_at = decision_row.snooze_until
WHERE decision_row.snooze_until IS NOT NULL
  AND alert_row.alert_id IS NULL;
