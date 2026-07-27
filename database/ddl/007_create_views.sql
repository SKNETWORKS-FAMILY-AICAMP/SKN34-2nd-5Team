CREATE OR REPLACE VIEW vw_latest_operator_decisions AS
SELECT current_decision.*
FROM operator_decisions AS current_decision
LEFT JOIN operator_decisions AS newer_decision
    ON newer_decision.model_version = current_decision.model_version
   AND newer_decision.sample_id = current_decision.sample_id
   AND newer_decision.decision_id > current_decision.decision_id
WHERE newer_decision.decision_id IS NULL;

CREATE OR REPLACE VIEW vw_reviewer_work_queue AS
SELECT
    cohort.model_version,
    cohort.sample_id,
    cohort.user_id,
    cohort.comparison_year,
    cohort.selection_year,
    cohort.target_year,
    cohort.prior_activity_available,
    cohort.scope,
    prediction.retained_score,
    prediction.weakened_score,
    prediction.stopped_score,
    prediction.priority_score,
    prediction.predicted_state,
    prediction.predicted_state_label,
    prediction.priority_rank,
    prediction.priority_top_percent,
    prediction.selected_for_crm,
    feature.baseline_review_count,
    feature.recent_review_count,
    feature.review_count_decline_rate,
    feature.baseline_active_months,
    feature.recent_active_months,
    feature.active_month_decline_rate,
    feature.baseline_recency_days,
    feature.recent_recency_days,
    feature.recency_increase_days,
    feature.baseline_mean_interval_days,
    feature.recent_mean_interval_days,
    feature.mean_interval_increase_days,
    feature.baseline_unique_business_count,
    feature.recent_unique_business_count,
    feature.unique_business_decline_rate,
    decision.decision_id,
    decision.manager_decision,
    decision.risk_type,
    decision.model_judgment,
    decision.decision_reason,
    decision.decision_owner,
    decision.decided_at,
    decision.playbook_id,
    decision.review_due_at
FROM cohort_samples AS cohort
JOIN reviewer_features AS feature
  ON feature.model_version = cohort.model_version
 AND feature.sample_id = cohort.sample_id
JOIN model_predictions AS prediction
  ON prediction.model_version = cohort.model_version
 AND prediction.sample_id = cohort.sample_id
LEFT JOIN vw_latest_operator_decisions AS decision
  ON decision.model_version = cohort.model_version
 AND decision.sample_id = cohort.sample_id;

CREATE OR REPLACE VIEW vw_reviewer_validation AS
SELECT
    queue.*,
    outcome.target_review_count,
    outcome.target_active_months,
    outcome.retention_state,
    outcome.churn
FROM vw_reviewer_work_queue AS queue
JOIN validation_outcomes AS outcome
  ON outcome.model_version = queue.model_version
 AND outcome.sample_id = queue.sample_id;

CREATE OR REPLACE VIEW vw_model_top20_summary AS
SELECT
    prediction.model_version,
    COUNT(*) AS total_users,
    SUM(prediction.selected_for_crm) AS target_users,
    SUM(outcome.retention_state <> 0) AS total_status_loss,
    SUM(
        prediction.selected_for_crm = 1
        AND outcome.retention_state <> 0
    ) AS status_loss_captured,
    SUM(
        prediction.selected_for_crm = 1
        AND outcome.retention_state = 2
    ) AS stopped_captured,
    SUM(
        prediction.selected_for_crm = 1
        AND outcome.retention_state = 1
    ) AS weakened_captured
FROM model_predictions AS prediction
JOIN validation_outcomes AS outcome
  ON outcome.model_version = prediction.model_version
 AND outcome.sample_id = prediction.sample_id
GROUP BY prediction.model_version;
