-- 결과의 issue_count가 모두 0이어야 한다.

SELECT 'operator_without_region' AS check_name, COUNT(*) AS issue_count
FROM auth_users
WHERE access_role = 'OPERATOR' AND region_code IS NULL
UNION ALL
SELECT 'viewer_with_region', COUNT(*)
FROM auth_users
WHERE access_role = 'VIEWER' AND region_code IS NOT NULL
UNION ALL
SELECT 'duplicate_active_operator_region', COUNT(*)
FROM (
    SELECT region_code
    FROM auth_users
    WHERE access_role = 'OPERATOR' AND status = 'APPROVED'
    GROUP BY region_code
    HAVING COUNT(*) > 1
) AS duplicated_region
UNION ALL
SELECT 'missing_expected_region_operator', 14 - COUNT(DISTINCT region_code)
FROM auth_users
WHERE access_role = 'OPERATOR'
  AND status = 'APPROVED'
  AND region_code IN ('PA','FL','IN','TN','LA','MO','AZ','NV','NJ','AB','ID','CA','IL','DE')
UNION ALL
SELECT 'missing_shared_viewer', ABS(COUNT(*) - 1)
FROM auth_users
WHERE username = 'retention_viewer'
  AND access_role = 'VIEWER'
  AND status = 'APPROVED';

SELECT region_code, username, full_name, status, last_login_at
FROM auth_users
WHERE access_role = 'OPERATOR'
ORDER BY region_code, username;

