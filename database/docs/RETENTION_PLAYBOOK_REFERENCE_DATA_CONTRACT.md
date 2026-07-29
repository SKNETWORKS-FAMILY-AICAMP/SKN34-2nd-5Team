# 리텐션 플레이북 기준 데이터 계약

## 목적

`DECISION_PLAYBOOKS`의 운영 문구를 MySQL에서도 조회할 수 있도록 정적 기준
데이터로 적재한다. 이 데이터는 모델 버전과 무관하며 v04 학습·예측 결과가
아니다.

현재 React와 보관된 Streamlit 앱은 계속 코드 상수를 사용한다. 이 계약은 향후
API 연결을 위한 DB 기준 데이터를 완성하는 범위이며 `operator_decisions`의 실제
운영 이력 저장을 활성화하지 않는다.

## 원천

```text
archive/app_streamlit_v04/core/insights.py
└─ DECISION_PLAYBOOKS
```

`STRATEGIES`와 `STATE_RECOMMENDATIONS`는 이번 적재 범위에 포함하지 않는다.

## 테이블

### retention_playbooks

관리자 판단마다 한 행을 저장한다.

| 항목 | 계약 |
|---|---|
| 행 수 | 4 |
| PK | `playbook_id` |
| 자연키 | `manager_decision` |
| 주요 내용 | 조건, 신호, 1차 행동, 채널, 고도화 필요, 성공 기준 초안 |

### retention_playbook_risk_actions

플레이북 안에서 위험 유형에 따라 달라지는 세부 전략을 저장한다.

| 항목 | 계약 |
|---|---|
| 행 수 | 6 |
| PK | `playbook_id + risk_type` |
| FK | `playbook_id → retention_playbooks.playbook_id` |

플레이북별 세부 전략 수는 다음과 같다.

| 관리자 판단 | 행 수 |
|---|---:|
| 리뷰 다시 시작 유도 | 2 |
| 리뷰 활동 늘리기 | 3 |
| 변화 지켜보기 | 1 |
| 이번엔 제외 | 0 |

## 적재 정책

`database/load/seed_reference_data.py`를 사용한다. 같은 명령을 다시 실행하면 부모
행은 갱신하고, 관리 대상 플레이북의 세부 전략은 코드 상수와 다시 동기화한다.
대상 DB 이름은 `--confirm-database`와 실제 연결 DB가 정확히 같아야 한다.

```bat
python database\load\seed_reference_data.py ^
  --confirm-database yelp_data
```

검증은 `database/validation/validate_reference_data.sql`을 사용한다.
