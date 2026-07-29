# React ↔ MySQL(`yelp_data`) 연결 계획 (v04)

React가 지금까지 읽던 정적 JSON(`app/src/data/*.json`,
`app/public/data/reviewer-details.json`)을 서비스 계층을 통한 DB 조회로
바꾸기 위한 데이터 조달 계약과 아키텍처 결정을 기록한다.

기존 JSON 파이프라인은 [`REACT_DATA_SOURCES_v04.md`](../REACT_DATA_SOURCES_v04.md)에,
DB 스키마와 적재 절차는 [`database/README.md`](../../database/README.md)와
[`database/docs/erd_v04.md`](../../database/docs/erd_v04.md)에 있다. 이 문서는
그 둘을 잇는 짝문서다.

작성 배경: 2026-07-30, 팀원이 구성한 `yelp_data` DB를 읽기 전용으로 검증하고,
React가 소비하는 필드를 하나씩 DB 컬럼과 대조한 뒤 정리한 계획.

---

## 0. 이 문서의 범위

- **다루는 것**: React 화면이 필요로 하는 값을 DB에서 어떻게 조달하는지,
  DB로 조달할 수 없는 값은 어디서 처리하고 언제 방식을 바꿀지.
- **다루지 않는 것**: DB 스키마·DDL·적재 로더. 이 파일들은 팀원 소유이며
  이 작업 범위에서 수정하지 않는다.

---

## 1. DB 검증 결과 (2026-07-30 기준)

`yelp_data`를 읽기 전용으로 확인한 결과, React 연결을 시작해도 되는 상태다.

| 항목 | 결과 |
|---|---|
| 테이블·뷰 | 22개 전부 존재 |
| 모델 버전 | v02·v03·v04 3개 적재 |
| v04 모델 해시 | `metadata.json` · 실제 joblib · DB 3자 일치 |
| 코호트·피처·검증 결과 | 각 37,953행 |
| 예측·권역 | 각 6,533행 |
| 월별 활동 | 67,814행, Test 표본 전원 최소 1개월 존재 |
| 참조 무결성 | 고아·중복 0건 |
| 월별 리뷰 수 합계 | 프로필 `baseline + recent`와 불일치 0건 |
| 운영 기준정보 | 플레이북 4행, 위험유형별 세부 전략 6행 |
| 시간 누수 방지 | `vw_reviewer_work_queue`에 정답 컬럼 노출 0건 |
| 적재 일관성 | `loaded_at`이 단일 구간(약 47초)에 집중, 부분 적재 흔적 없음 |

`operator_decisions`는 0행이며, 운영 입력을 받기 전이므로 정상이다.

---

## 2. 필드 조달 분류

React가 소비하는 필드를 다섯 가지로 나눈다.

| 분류 | 의미 | 처리 위치 |
|---|---|---|
| **A** | DB 원자료 그대로 | SQL |
| **B** | DB에 있으나 이름이 다름 | SQL + 별칭 |
| **C** | DB 값의 단순 변환(라벨·포맷) | 서비스 계층 |
| **D** | 임계치 로직이 필요한 파생 속성 | 서비스 계층 (3절) |
| **E** | DB에 근거가 없는 정적 콘텐츠 | 서비스 계층 (4절) |

### 2-1. 파일별 분포

| 파일 | A | B | C | D | E |
|---|---:|---:|---:|---:|---:|
| `operations.json` (14) | 12 | – | 1 | – | 1 |
| `reviewers.json` (23) | 14 | 1 | 4 | 3 | 1 |
| `reviewer-details.json` (7) | 5 | – | 1 | 1 | – |
| `trust.json` (11) | 9 | 1 | 2 | – | – |
| `regional.json` (7) | 6 | – | – | – | 1 |
| `playbooks.json` (9) | 8 | – | 1 | – | – |
| `strategies.json` (2) | – | – | – | – | 2 |

### 2-2. 화면별 조달 상태

| 화면 | DB 조달 | 서비스 계층 필요 |
|---|---|---|
| 운영 홈 `/` | `vw_model_top20_summary`, `model_predictions` | `dataMode`(앱 상수) |
| 리뷰어 관리 `/reviewers` | `vw_reviewer_work_queue` | 위험유형, 근거 문구, 추천 문구 |
| 리뷰어 상세 `/reviewers/:id` | 위 + `reviewer_monthly_activity`, `vw_reviewer_validation` | 근거 목록, 전략 카드 |
| 콘텐츠 위험 `/regional` | `vw_regional_risk_summary` | 없음 |
| 플레이북 `/playbooks` | `retention_playbooks`, `retention_playbook_risk_actions` | `modelJudgment`(2-3 참고) |
| Trust Center `/trust` | 평가 지표 5종 + `model_binary_*` | 없음 |

### 2-3. `DECISION_STATE_MAP`에 의존하는 두 필드

`DECISION_STATE_MAP`
([shared/retention/insights.py:85](../../shared/retention/insights.py:85))은
예측 상태(0·1·2)와 관리자 판단 이름을 잇는 3줄짜리 대응표다. 대응표 자체는
코드에 있지만 양쪽 값이 모두 DB에 있어, 새 컬럼 없이 C(단순 변환)로 처리한다.

| 필드 | 화면 | DB 입력값 |
|---|---|---|
| `playbooks.modelJudgment` | 플레이북 카드의 "모델 중단 우세" 배지 ([PlaybookPage.jsx:350](../../app/src/pages/PlaybookPage.jsx:350)) | `retention_playbooks.manager_decision` (역매핑) |
| `reviewers.recommendedDecision` | 목록의 추천 판단 | `model_predictions.predicted_state` |

같은 화면의 `recommendedReview`는 이 대응표가 아니라
`STATE_RECOMMENDATIONS`의 문구를 쓰므로 E로 분류한다(4절).

---

## 3. 결정 — 파생 속성은 서비스 계층에서 계산한다

### 3-1. 대상

| 필드 | 화면 | 계산 함수 |
|---|---|---|
| `riskType` | 목록·상세 | `classify_risk_type()` ([shared/retention/insights.py:147](../../shared/retention/insights.py:147)) |
| `coreSignal` | 목록 | `SIGNAL_LABELS[riskType]` |
| `metrics` | 목록 | `risk_signals()[:2]` ([shared/retention/insights.py:182](../../shared/retention/insights.py:182)) |
| `evidence` | 상세 | `risk_signals()[:3]` |

원자료는 전부 `reviewer_features`에 있고, 계산만 필요하다.

### 3-2. 방식

`shared/retention/insights.py`의 함수를 **그대로 import해서** 사용한다. SQL이나
JS로 재구현하지 않는다. 규칙이 두 곳에 존재하면 임계치를 조정할 때 조용히
어긋나기 때문이다 — `scripts/export_frontend_data.py` 상단 주석이 같은 이유로
JS 재구현을 이미 배제하고 있다.

애초 계획서 초안에서는 `api/insights_bridge.py`가 `archive/app_streamlit_v04`를
`sys.path`에 얹어 `core.insights`를 import했는데, 그 경로가 `core.data`(streamlit
의존)를 우회로 끌고 들어올 여지가 있다는 게 나중에 드러나 정리했다(6-2절).
지금은 API가 `archive/`를 전혀 거치지 않는다.

```text
shared/retention/insights.py (규칙 — 버전 관리·테스트 대상, streamlit 비의존)
        ↓ import
서비스 계층 (조회 시 계산)
        ↓ JSON
React
```

Streamlit(`archive/app_streamlit_v04/`)과 `scripts/export_frontend_data.py`도
같은 `shared/retention/`을 참조한다 — 규칙이 세 소비자(Streamlit·API·export
스크립트) 모두에게 한 곳에만 존재한다.

### 3-3. 이 방식을 택한 이유

- 대상이 6,533행이라 전량 로드해도 부담이 없다.
- 모델 재학습 시에만 갱신되며 실시간 갱신 요구가 없다.
- 배치 스케줄러·재실행 정책이 아직 없다.
- 규칙을 코드에 두는 한, 나중에 배치 방식으로 바꿔도 로직을 다시 짜지 않는다.

### 3-4. 배치 사전계산으로 전환할 조건

아래 중 하나라도 해당되면 야간 배치가 계산 결과를 테이블에 적재하는 방식으로
옮긴다. 이때도 **규칙은 코드에 두고 결과만 저장**하며, 어떤 규칙 버전이
만든 값인지 함께 기록한다.

1. 대상자가 늘어 SQL 레벨 페이지네이션(`WHERE riskType = ? LIMIT n`)이 필요해질 때
2. CRM·발송 시스템과 연동되어 "언제 왜 이 사람이 대상이었나"를 소명해야 할 때
3. 분석 담당자가 SQL로 세그먼트를 직접 집계하려 할 때

현재 리뷰어 관리 화면의 위험유형 필터와 플레이북 화면의 판단별 집계가 이미
이 성격의 조회라, 1번 조건은 규모가 커지면 가장 먼저 걸린다.

### 3-5. 하지 않을 것

임계치 판단을 SQL `CASE WHEN`이나 생성 컬럼으로 이식하지 않는다. 규칙이
Python과 SQL 두 곳에 중복되어 어긋나는 것이 이 결정에서 막으려는 실패다.

---

## 4. 결정 — 정적 콘텐츠는 코드 상수로 유지한다

### 4-1. 대상

`strategies.json`이 담는 두 조회표로, 리뷰어 상세 화면의 "추천 전략"
카드([ReviewerDetailPage.jsx:141](../../app/src/pages/ReviewerDetailPage.jsx:141))와
목록 화면의 "추천 검토" 열에 쓰인다.

| 조회표 | 행 수 | 화면 위치 |
|---|---:|---|
| `STATE_RECOMMENDATIONS` (byState) | 3 | 전략 카드 제목·설명 |
| `STRATEGIES` (byRiskType) | 5 | 전략 카드 보조 조치·채널 |

리뷰어마다 달라지는 값이 아니라, 상태와 위험유형이 같으면 전원이 같은 문구를
본다.

### 4-2. 이 방식을 택한 이유

- 8줄짜리 정적 텍스트이며 `model_version`과 무관하다(모델이 바뀌어도 문구는
  그대로라 버전 키를 둘 자리가 없다).
- 어떤 트랜잭션 테이블도 이 값을 FK로 참조하지 않는다.
- 관리 화면 없이 테이블만 만들면 문구 수정에 SQL을 직접 써야 해서, 변경
  이력·리뷰 절차·환경 간 동기화를 모두 잃는다. 코드 상수보다 나빠진다.

### 4-3. `retention_playbooks`는 DB로 간 것과 무엇이 다른가

같은 운영 문구인데 처리가 갈린 기준은 **트랜잭션 데이터가 참조하는가**이다.

`operator_decisions.playbook_id`가 `retention_playbooks`를 FK로 참조하므로,
"어떤 관리자가 어떤 플레이북을 근거로 판단했다"는 기록이 쌓인다. 안정적인
ID와 이력이 필요해 DB에 있어야 한다. `strategies`는 참조하는 기록이 없고
화면 표시가 전부다.

### 4-4. DB로 전환할 조건

운영자가 배포 없이 문구를 수정해야 하는 요구가 생길 때 옮긴다. 이때
**테이블만 만들지 말고 관리 화면과 함께** 도입한다. 다국어나 A/B 문구
실험이 필요해지는 경우도 같은 시점으로 본다.

---

## 5. 구현 시 주의사항

### 5-1. 컬럼 이름 매핑

| 코드·JSON 기준 | DB 컬럼 |
|---|---|
| `crm_target` | `model_predictions.selected_for_crm` |
| `rank` | `feature_importance.rank_no`, `feature_group_importance.rank_no` |

### 5-2. 사후 검증 값은 전용 View로만 조회한다

`reviewer-details.json`의 `actual`(타깃 연도 실제 리뷰 수·활동 월·상태)은
`vw_reviewer_work_queue`에 **의도적으로 포함되지 않는다**. 필요할 때만
`vw_reviewer_validation`을 명시적으로 조회한다. 운영 화면이 미래 결과를 보고
판단하는 것을 막기 위한 설계이므로, 편의를 이유로 운영 조회에 정답 컬럼을
합치지 않는다.

### 5-3. v02 Top-K는 split 필터가 필요하다

`model_binary_topk_metrics`에는 `final_test` 8행과 `validation` 8행이 함께
있는데, Trust Center의 v02 블록은 `final_test`만 쓴다. `WHERE split =
'final_test'` 필터를 반드시 건다.

### 5-4. 제거 가능한 우회 코드

`scripts/export_frontend_data.py`의 `FEATURE_GROUP_LABELS`는 리포트 CSV의
`feature_group_label`이 cp949로 깨져 들어오는 문제 때문에 ascii 키를 한글
라벨로 직접 매핑하던 우회다. DB에는 `리뷰 활동량` · `작성 간격` ·
`음식점 탐색`이 정상 저장되어 있으므로, DB 조회로 전환하면 이 매핑은 필요
없다.

### 5-5. 3클래스와 이진 모델의 스키마 차이

v03·v04는 3클래스 평가 테이블을 공유하지만, v02는 이진 이탈 분류라
`model_binary_validation_metrics` · `model_binary_topk_metrics`를 쓴다.
혼동행렬도 v02는 `active` / `stopped` 두 라벨이고 v03·v04는 3클래스 라벨이라
그대로 섞이지 않는다. Trust Center에서 v02·v03 블록이 v04 수치와 접힌 채로
분리되어 있는 현재 구성을 유지한다.

---

## 6. 의도적으로 하지 않은 것

- **DB 스키마·로더 수정**: `database/` 아래 파일은 팀원 소유이며 이 작업에서
  건드리지 않는다. 필요한 사항은 의견으로 전달한다.
- **위험유형 계산 결과의 테이블 적재**: 3-4의 전환 조건에 해당하기 전까지
  하지 않는다.
- **`strategies` 테이블 신설**: 4-4의 전환 조건에 해당하기 전까지 하지 않는다.
- **관리자 판단(`operator_decisions`) 저장 방식 변경**: v05로 미룬다. 상세는
  6-1 참고.

### 6-1. 관리자 판단 DB 저장 — v05 유예

React는 계속 `app/src/services/decisionStorage.js`의 브라우저 저장을 쓴다.
DB에 `operator_decisions` 테이블이 준비되어 있고 0행이지만, 이번 작업에서
쓰기 경로를 붙이지 않는다.

[`REACT_V04_PARITY_PLAN.md`](REACT_V04_PARITY_PLAN.md) 0절이 이미 같은 결정을
기록하고 있어, 이는 새 결정이 아니라 기존 결정의 유지다. 로드맵 수준의 항목은
[`BUSINESS_SCENARIOS.md`](../BUSINESS_SCENARIOS.md) 5절의 "실제 개입 이력 및
성과 관리"와 [`DEC-011`](../decisions/DEC-011_retention_operating_playbook_policy.md)의
"제외 사유·담당자·재검토 시점의 영구 이력 저장"에 있다. 이 절은 그 방향을
실제로 구현할 때 마주치는 **기술적 제약**을 남기는 데 목적이 있다.

#### 블로커 — 판단 취소를 표현할 방법이 없다

React에는 판단 취소 기능이 있다
([ReviewerDetailPage.jsx:152](../../app/src/pages/ReviewerDetailPage.jsx:152)의
`removeDecision()`). localStorage에서는 키를 지우면 끝이지만,
`operator_decisions`는 `decision_id`가 AUTO_INCREMENT인 이력 누적 구조이고
`vw_latest_operator_decisions`가 가장 큰 `decision_id`를 최신으로 뽑는다.
취소를 표현할 자리가 설계에 없다.

| 방법 | 문제 |
|---|---|
| 행 DELETE | 감사 이력이 사라져 이 테이블의 존재 이유와 충돌 |
| "취소" 행 INSERT | `manager_decision`이 NOT NULL인데 플레이북 4종에 없는 값이 들어가 판단별 집계가 깨짐 |
| 상태 컬럼(`is_active`·`status`) 추가 | 정석이지만 `database/ddl/004_create_operation_tables.sql` 변경이 필요 |

세 번째가 맞는 방향이며, 팀원 소유 파일의 스키마 변경이라 이번 범위에서
진행하지 않는다.

#### 함께 결정해야 할 것

- **담당자 식별**: React에 인증이 없어 `decision_owner`가 전부 NULL이 된다.
  `idx_operator_decisions_owner_due` 인덱스가 `(decision_owner, review_due_at)`에
  걸려 있는 것으로 보아 DB 설계는 담당자 개념을 전제한다.
- **저장 범위 변경의 체감**: 브라우저별 저장에서 공유 저장으로 바뀌면
  "판단 완료" 카운트가 개인 작업량에서 팀 전체 작업량으로 의미가 달라지고,
  같은 리뷰어를 동시에 판단할 때 나중 것이 조용히 최신이 된다.
- **입력 UI 확장 여부**: `decision_reason`·`review_due_at`은 현재 화면에
  입력란이 없다. DecisionPanel은 4개 선택지만 받는다.
- **안내 문구 갱신**: [DecisionPanel.jsx:127](../../app/src/components/reviewer-detail/DecisionPanel.jsx:127)이
  "담당자·CRM·감사 이력은 아직 연결되지 않았다"고 표시 중이다.

#### 막히지 않는 부분

`retention_playbooks`에 `UNIQUE KEY uq_retention_playbooks_manager_decision`이
있어, React가 저장하는 판단 문자열로 `playbook_id`를 1:1로 찾을 수 있다.
FK 연결 자체는 문제가 없다.

#### 이번 작업에서의 주의

`vw_reviewer_work_queue`는 `operator_decisions`를 LEFT JOIN하므로 판단 관련
컬럼(`manager_decision`·`decided_at` 등)이 전부 NULL로 딸려온다. React는 판단을
localStorage에서 읽으므로, **API 응답의 NULL이 localStorage 상태를 덮어쓰지
않도록** 서비스 계층에서 이 컬럼들을 제외하고 내려준다.

### 6-2. `shared/retention/` 분리 — 완료 (2026-07-30)

6개 화면 전환 직후, API가 `core.data`(streamlit 의존)를 두 경로로 간접
import하고 있다는 게 드러났다:

```text
api/reviewer_bridge.py → core.data._normalize_profiles → import streamlit
api/reviewer_bridge.py → scripts/export_frontend_data.py 전체 import
                        → 최상단 from core.data import load_app_data
                        → import streamlit
```

`_normalize_profiles`/`build_row`/`build_detail` 등은 함수 자체가
streamlit·DB·파일 I/O에 의존하지 않는 순수 로직이었는데, **그 로직이 사는
파일**(`core/data.py`, `scripts/export_frontend_data.py`)이 streamlit을
최상단에서 import하고 있어서 이름 하나만 가져와도 무거운 패키지가 따라왔다.

**조치**: 순수 로직을 `shared/retention/`(`formatters.py`/`insights.py`/
`profile_normalization.py`/`frontend_serializer.py`)으로 옮기고,
Streamlit·API·`scripts/export_frontend_data.py` 셋 다 이 모듈만 참조하도록
정리했다. `archive/app_streamlit_v04/core/{insights,formatters}.py`는
`shared.retention`을 재노출하는 호환 wrapper로 남겨 기존 import 경로
(`database/load/seed_reference_data.py`, `tests/test_demo_contract.py` 등
팀원·테스트 코드 포함)를 안 건드리고 유지했다. `load_app_data`는
`scripts/export_frontend_data.py`의 `main()` 안으로 지연 import해서,
export 스크립트를 그냥 import만 하는 것(API가 하는 일)만으로는 streamlit이
안 딸려오게 했다. 상세 설계는 `AGENTS.md` 4절 참고.

검증: `import api.main` 시 `'streamlit' not in sys.modules`, Streamlit
6개 view 전체 정상 동작, `export_frontend_data.py` 재실행 시 산출 JSON
해시가 리팩터링 전과 동일, API↔JSON 6,533건 전량 재대조 0건 불일치,
`pytest tests/` 회귀 없음, `git diff -- database pipeline` 빈 결과 — 전부
확인 완료. `api/reviewer_bridge.py`는 더 이상 필요 없어 삭제했다.

---

## 7. 참고

- [`REACT_DATA_SOURCES_v04.md`](../REACT_DATA_SOURCES_v04.md) — 현재 JSON 파이프라인
- [`database/README.md`](../../database/README.md) — DB 구성·적재 절차
- [`database/docs/erd_v04.md`](../../database/docs/erd_v04.md) — 테이블 관계와 키 설계
- [`database/docs/YELP_DATA_COMPLETE_LOAD_CONTRACT.md`](../../database/docs/YELP_DATA_COMPLETE_LOAD_CONTRACT.md) — 전체 적재 계약
- [`REACT_V04_PARITY_PLAN.md`](REACT_V04_PARITY_PLAN.md) — Streamlit 대비 화면 통합 계획
- [`AGENTS.md`](../../AGENTS.md) 4절 — `shared/retention/`이 계산·정규화·직렬화
  로직의 source of truth라는 프로젝트 전역 규칙
