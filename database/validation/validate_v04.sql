-- DBeaver에서 검증할 DB를 명시적으로 선택한 뒤 실행한다.
-- 예: USE yelp_retention_v04_derived_dev;
SELECT DATABASE() AS validation_database;

-- 1. 모델 계약: 정확히 v04 1행
SELECT
    model_version,
    model_name,
    feature_count,
    test_selection_year,
    test_target_year,
    test_samples,
    priority_target_rate,
    model_sha256
FROM model_versions
WHERE model_version = 'v04';

-- 2. 전체 행 수: cohort/features/outcomes는 각각 37,953
SELECT 'cohort_samples' AS table_name, COUNT(*) AS rows_found
FROM cohort_samples
WHERE model_version = 'v04'
UNION ALL
SELECT 'reviewer_features', COUNT(*)
FROM reviewer_features
WHERE model_version = 'v04'
UNION ALL
SELECT 'validation_outcomes', COUNT(*)
FROM validation_outcomes
WHERE model_version = 'v04'
UNION ALL
SELECT 'model_predictions', COUNT(*)
FROM model_predictions
WHERE model_version = 'v04';

-- 3. 중복: 세 결과가 모두 0이어야 함
SELECT 'cohort_duplicate' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT sample_id
    FROM cohort_samples
    WHERE model_version = 'v04'
    GROUP BY sample_id
    HAVING COUNT(*) > 1
) AS duplicated
UNION ALL
SELECT 'feature_without_cohort', COUNT(*)
FROM reviewer_features AS feature
LEFT JOIN cohort_samples AS cohort
  ON cohort.model_version = feature.model_version
 AND cohort.sample_id = feature.sample_id
WHERE feature.model_version = 'v04'
  AND cohort.sample_id IS NULL
UNION ALL
SELECT 'prediction_without_cohort', COUNT(*)
FROM model_predictions AS prediction
LEFT JOIN cohort_samples AS cohort
  ON cohort.model_version = prediction.model_version
 AND cohort.sample_id = prediction.sample_id
WHERE prediction.model_version = 'v04'
  AND cohort.sample_id IS NULL;

-- 4. Test 시간 구조: 2018 → 2019, 6,533행
SELECT
    selection_year,
    target_year,
    COUNT(*) AS users
FROM cohort_samples
WHERE model_version = 'v04'
  AND split_v04 = 'test'
GROUP BY selection_year, target_year;

-- 5. 실제 상태 분포: 유지 2,584 / 약화 3,065 / 중단 884
SELECT
    outcome.retention_state,
    COUNT(*) AS users
FROM validation_outcomes AS outcome
JOIN cohort_samples AS cohort
  ON cohort.model_version = outcome.model_version
 AND cohort.sample_id = outcome.sample_id
WHERE outcome.model_version = 'v04'
  AND cohort.split_v04 = 'test'
GROUP BY outcome.retention_state
ORDER BY outcome.retention_state;

-- 6. CRM 상위 20%: 1,307명
SELECT
    COUNT(*) AS total_predictions,
    SUM(selected_for_crm) AS crm_target_users,
    MIN(priority_rank) AS min_rank,
    MAX(priority_rank) AS max_rank
FROM model_predictions
WHERE model_version = 'v04';

-- 7. 비교 활동 없음: Test 1,692명
SELECT COUNT(*) AS no_prior_activity_users
FROM cohort_samples
WHERE model_version = 'v04'
  AND split_v04 = 'test'
  AND prior_activity_available = 0;

-- 8. Top 20% 포착: 지위 상실 1,142 / 중단 481 / 약화 661
SELECT *
FROM vw_model_top20_summary
WHERE model_version = 'v04';

-- 9. 운영 View에 검증 정답 컬럼이 없어야 함: 결과 0행
SELECT column_name
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'vw_reviewer_work_queue'
  AND column_name IN (
      'target_review_count',
      'target_active_months',
      'retention_state',
      'churn'
  );

-- 10. 핵심 평가 파일 적재 건수
SELECT 'model_validation_metrics' AS table_name, COUNT(*) AS rows_found
FROM model_validation_metrics
WHERE model_version = 'v04'
UNION ALL
SELECT 'model_topk_metrics', COUNT(*)
FROM model_topk_metrics
WHERE model_version = 'v04'
UNION ALL
SELECT 'model_confusion_matrix', COUNT(*)
FROM model_confusion_matrix
WHERE model_version = 'v04'
UNION ALL
SELECT 'feature_importance', COUNT(*)
FROM feature_importance
WHERE model_version = 'v04'
UNION ALL
SELECT 'feature_group_importance', COUNT(*)
FROM feature_group_importance
WHERE model_version = 'v04';

-- 11. 파생 리뷰어 데이터 적재 건수
SELECT 'reviewer_region' AS table_name, COUNT(*) AS rows_found
FROM reviewer_region
WHERE model_version = 'v04'
UNION ALL
SELECT 'reviewer_monthly_activity', COUNT(*)
FROM reviewer_monthly_activity
WHERE model_version = 'v04';

-- 12. 파생 데이터 PK 중복: 두 결과 모두 0이어야 함
SELECT 'reviewer_region_duplicate' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT sample_id
    FROM reviewer_region
    WHERE model_version = 'v04'
    GROUP BY sample_id
    HAVING COUNT(*) > 1
) AS duplicated_region
UNION ALL
SELECT 'reviewer_monthly_duplicate', COUNT(*)
FROM (
    SELECT sample_id, `year_month`
    FROM reviewer_monthly_activity
    WHERE model_version = 'v04'
    GROUP BY sample_id, `year_month`
    HAVING COUNT(*) > 1
) AS duplicated_month;

-- 13. 파생 데이터 참조·시간 계약: 세 결과 모두 0이어야 함
SELECT 'region_without_cohort' AS check_name, COUNT(*) AS issue_count
FROM reviewer_region AS region
LEFT JOIN cohort_samples AS cohort
  ON cohort.model_version = region.model_version
 AND cohort.sample_id = region.sample_id
WHERE region.model_version = 'v04'
  AND cohort.sample_id IS NULL
UNION ALL
SELECT 'monthly_without_cohort', COUNT(*)
FROM reviewer_monthly_activity AS activity
LEFT JOIN cohort_samples AS cohort
  ON cohort.model_version = activity.model_version
 AND cohort.sample_id = activity.sample_id
WHERE activity.model_version = 'v04'
  AND cohort.sample_id IS NULL
UNION ALL
SELECT 'prediction_without_region', COUNT(*)
FROM model_predictions AS prediction
LEFT JOIN reviewer_region AS region
  ON region.model_version = prediction.model_version
 AND region.sample_id = prediction.sample_id
WHERE prediction.model_version = 'v04'
  AND region.sample_id IS NULL
UNION ALL
SELECT 'prediction_without_monthly_activity', COUNT(*)
FROM model_predictions AS prediction
LEFT JOIN (
    SELECT DISTINCT model_version, sample_id
    FROM reviewer_monthly_activity
    WHERE model_version = 'v04'
) AS activity
  ON activity.model_version = prediction.model_version
 AND activity.sample_id = prediction.sample_id
WHERE prediction.model_version = 'v04'
  AND activity.sample_id IS NULL
UNION ALL
SELECT 'monthly_outside_feature_window', COUNT(*)
FROM reviewer_monthly_activity AS activity
JOIN cohort_samples AS cohort
  ON cohort.model_version = activity.model_version
 AND cohort.sample_id = activity.sample_id
WHERE activity.model_version = 'v04'
  AND CAST(LEFT(activity.`year_month`, 4) AS UNSIGNED)
      NOT BETWEEN cohort.comparison_year AND cohort.selection_year;

-- 14. 월별 리뷰 합계와 프로필 피처 합계: issue_count=0이어야 함
SELECT COUNT(*) AS issue_count
FROM (
    SELECT
        activity.sample_id,
        SUM(activity.review_count) AS monthly_reviews,
        feature.baseline_review_count + feature.recent_review_count
            AS expected_reviews
    FROM reviewer_monthly_activity AS activity
    JOIN reviewer_features AS feature
      ON feature.model_version = activity.model_version
     AND feature.sample_id = activity.sample_id
    WHERE activity.model_version = 'v04'
    GROUP BY
        activity.sample_id,
        feature.baseline_review_count,
        feature.recent_review_count
    HAVING monthly_reviews <> expected_reviews
) AS mismatched_review_totals;

-- 15. 권역 View 합계: 6,533명 / CRM 1,307명
SELECT
    COUNT(*) AS regions,
    SUM(total_reviewers) AS total_reviewers,
    SUM(crm_targets) AS crm_targets
FROM vw_regional_risk_summary
WHERE model_version = 'v04';
