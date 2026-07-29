-- DBeaver에서 검증할 DB를 명시적으로 선택한 뒤 실행한다.
-- 예: USE yelp_data;
SELECT DATABASE() AS validation_database;

-- 1. 공통 플레이북은 정확히 4행이어야 한다.
SELECT COUNT(*) AS playbook_rows
FROM retention_playbooks
WHERE playbook_id IN (
    'review_restart',
    'review_activity',
    'monitor_change',
    'exclude_now'
);

-- 2. 위험 유형별 세부 조치는 정확히 6행이어야 한다.
SELECT COUNT(*) AS risk_action_rows
FROM retention_playbook_risk_actions
WHERE playbook_id IN (
    'review_restart',
    'review_activity',
    'monitor_change',
    'exclude_now'
);

-- 3. 플레이북별 세부 조치 수는 2 / 3 / 1 / 0이어야 한다.
SELECT
    playbook.playbook_id,
    playbook.manager_decision,
    playbook.display_order,
    COUNT(action.risk_type) AS risk_action_rows
FROM retention_playbooks AS playbook
LEFT JOIN retention_playbook_risk_actions AS action
  ON action.playbook_id = playbook.playbook_id
WHERE playbook.playbook_id IN (
    'review_restart',
    'review_activity',
    'monitor_change',
    'exclude_now'
)
GROUP BY
    playbook.playbook_id,
    playbook.manager_decision,
    playbook.display_order
ORDER BY playbook.display_order;

-- 4. 필수 공통 내용이 비어 있는 행은 0행이어야 한다.
SELECT COUNT(*) AS incomplete_playbook_rows
FROM retention_playbooks
WHERE playbook_id IN (
    'review_restart',
    'review_activity',
    'monitor_change',
    'exclude_now'
)
  AND (
      TRIM(condition_text) = ''
      OR TRIM(signals_text) = ''
      OR TRIM(primary_action) = ''
      OR TRIM(channel) = ''
      OR TRIM(needs_upgrade) = ''
      OR TRIM(success_criteria) = ''
  );

-- 5. 세부 조치가 존재하지 않는 부모를 참조하는 행은 0행이어야 한다.
SELECT COUNT(*) AS orphan_risk_action_rows
FROM retention_playbook_risk_actions AS action
LEFT JOIN retention_playbooks AS playbook
  ON playbook.playbook_id = action.playbook_id
WHERE playbook.playbook_id IS NULL;
