-- DBeaver에서 검증할 DB를 명시적으로 선택한 뒤 실행한다.
-- 예: USE yelp_data;
SELECT DATABASE() AS validation_database;

-- 1. 비교 버전 계약: v02/v03 각 1행, 리포트 전용이라 model_sha256은 NULL
SELECT
    model_version,
    model_name,
    problem_type,
    feature_count,
    test_selection_year,
    test_target_year,
    test_samples,
    priority_target_rate,
    model_sha256,
    JSON_UNQUOTE(
        JSON_EXTRACT(metadata_json, '$.artifact_scope')
    ) AS artifact_scope
FROM model_versions
WHERE model_version IN ('v02', 'v03')
ORDER BY model_version;

-- 2. v03: 기존 다중분류 평가 테이블 재사용
SELECT 'model_validation_metrics' AS table_name, COUNT(*) AS rows_found
FROM model_validation_metrics
WHERE model_version = 'v03'
UNION ALL
SELECT 'model_topk_metrics', COUNT(*)
FROM model_topk_metrics
WHERE model_version = 'v03'
UNION ALL
SELECT 'model_confusion_matrix', COUNT(*)
FROM model_confusion_matrix
WHERE model_version = 'v03'
UNION ALL
SELECT 'feature_importance', COUNT(*)
FROM feature_importance
WHERE model_version = 'v03'
UNION ALL
SELECT 'feature_group_importance', COUNT(*)
FROM feature_group_importance
WHERE model_version = 'v03';

-- 3. v03 final_test: 4,157명 / 통합 Top 20% 832명
SELECT
    SUM(users) AS final_test_users
FROM model_confusion_matrix
WHERE model_version = 'v03'
  AND split = 'final_test';

SELECT
    target_users,
    status_loss_captured,
    status_loss_precision,
    status_loss_recall,
    status_loss_lift
FROM model_topk_metrics
WHERE model_version = 'v03'
  AND split = 'final_test'
  AND ranking = 'unified'
  AND target_rate = 0.20000;

-- 4. v02: 이진 전용 평가 테이블 + 공용 혼동행렬/중요도 테이블
SELECT 'model_binary_validation_metrics' AS table_name, COUNT(*) AS rows_found
FROM model_binary_validation_metrics
WHERE model_version = 'v02'
UNION ALL
SELECT 'model_binary_topk_metrics', COUNT(*)
FROM model_binary_topk_metrics
WHERE model_version = 'v02'
UNION ALL
SELECT 'model_confusion_matrix', COUNT(*)
FROM model_confusion_matrix
WHERE model_version = 'v02'
UNION ALL
SELECT 'feature_importance', COUNT(*)
FROM feature_importance
WHERE model_version = 'v02'
UNION ALL
SELECT 'feature_group_importance', COUNT(*)
FROM feature_group_importance
WHERE model_version = 'v02';

-- 5. v02 final_test: 4,157명 / Top 20% 832명 / 실제 중단 346명 포착
SELECT
    validation_samples,
    precision_score,
    recall_score,
    f1,
    roc_auc,
    pr_auc
FROM model_binary_validation_metrics
WHERE model_version = 'v02'
  AND split = 'final_test';

SELECT
    target_users,
    captured_churn_users,
    precision_at_k,
    recall_at_k,
    lift_at_k
FROM model_binary_topk_metrics
WHERE model_version = 'v02'
  AND split = 'final_test'
  AND target_rate = 0.20000;
