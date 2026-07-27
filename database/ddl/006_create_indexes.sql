CREATE INDEX idx_cohort_samples_user_year
    ON cohort_samples (user_id, selection_year);

CREATE INDEX idx_cohort_samples_split
    ON cohort_samples (model_version, split_v04, selection_year);

CREATE INDEX idx_model_predictions_queue
    ON model_predictions (
        model_version,
        selected_for_crm,
        priority_rank
    );

CREATE INDEX idx_model_predictions_state
    ON model_predictions (model_version, predicted_state, priority_rank);

CREATE INDEX idx_validation_outcomes_state
    ON validation_outcomes (model_version, retention_state);

CREATE INDEX idx_operator_decisions_sample_time
    ON operator_decisions (model_version, sample_id, decided_at);

CREATE INDEX idx_operator_decisions_owner_due
    ON operator_decisions (decision_owner, review_due_at);
