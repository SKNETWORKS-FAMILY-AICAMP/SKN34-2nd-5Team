-- 모든 issue_count가 0이어야 한다.

SELECT 'member_without_matching_reviewer' AS check_name, COUNT(*) AS issue_count
FROM target_list_members AS member_row
LEFT JOIN cohort_samples AS sample
  ON sample.model_version = member_row.model_version
 AND sample.sample_id = member_row.sample_id
 AND sample.user_id = member_row.reviewer_user_id
WHERE sample.sample_id IS NULL;

SELECT 'member_without_parent_list' AS check_name, COUNT(*) AS issue_count
FROM target_list_members AS member_row
LEFT JOIN target_lists AS list_row
  ON list_row.list_id = member_row.list_id
WHERE list_row.list_id IS NULL;

SELECT 'list_missing_creator' AS check_name, COUNT(*) AS issue_count
FROM target_lists
WHERE created_by_subject = '' OR created_by_name = '';

SELECT 'duplicate_member_in_list' AS check_name, COUNT(*) AS issue_count
FROM (
  SELECT list_id, reviewer_user_id, COUNT(*) AS occurrences
  FROM target_list_members
  GROUP BY list_id, reviewer_user_id
  HAVING occurrences > 1
) AS duplicated;
