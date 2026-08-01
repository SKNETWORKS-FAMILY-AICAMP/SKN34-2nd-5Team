# v05 파생 데이터·DB 실행 안내

## 1. 목적

`v05/`는 발표 전 React 고도화에 필요한 추가 파생 로직과 DB 적재 파일을 기존
`pipeline/`, `database/` 작업과 분리해 관리한다. 기존 v04 모델, 코호트, 원본
데이터의 정의를 바꾸지 않으며 해당 경로는 읽기 전용으로 참조한다.

런타임 데이터 흐름은 다음과 같다.

```text
v04 원본·코호트·공간 데이터
  → v05/pipeline 파생
  → data/processed/*.parquet
  → v05/database/load 적재
  → MySQL yelp_data
  → FastAPI api/
  → React app/
```

Parquet는 생성·검증·복구용 중간 산출물이고, React 런타임의 기준은
FastAPI를 통해 조회하는 MySQL `yelp_data`다.

## 2. 디렉터리

```text
v05/
├─ pipeline/
│  ├─ build_spatial_v04.py
│  ├─ derive_recommendations_v04.py
│  ├─ derive_regional_inflow_v04.py
│  └─ derive_regional_review_supply_v04.py
└─ database/
   ├─ ddl/
│  ├─ 011_create_spatial_tables.sql
│  ├─ 012_create_spatial_views.sql
│  ├─ 013_create_v05_derived_tables.sql
│  ├─ 014_create_retention_operation_tables.sql
│  └─ 015_create_target_list_tables.sql
   ├─ load/
   │  ├─ load_spatial_v04.py
   │  └─ load_v05_derived.py
   └─ validation/
      ├─ validate_v05_derived.sql
      ├─ validate_retention_operations.sql
      └─ validate_target_lists.sql
```

## 3. 파생 산출물

| 기능 | Parquet | 현재 결과 |
|---|---|---:|
| G-1 개인 맞춤 음식점 추천 | `reviewer_restaurant_recommendations_v04.parquet` | 19,351행 · 6,456명 |
| G-2 권역별 전체 리뷰 공급 | `regional_review_supply_v04.parquet` | 140행 |
| G-3/G-5 공간 요약 | `spatial/reviewer_spatial_summaries_v04.parquet` | 11,374행 |
| G-4 리뷰어 권역 이력 | `reviewer_region_history_v04.parquet` | 37,953행 |
| G-4 권역별 신규 진입 | `regional_newcomers_v04.parquet` | 126행 |

모든 파일은 `data/processed/` 아래에 생성되며 `.gitignore` 대상이다.

## 4. 파생 실행 순서

프로젝트 루트에서 가상환경 Python으로 실행한다.

```powershell
venv\Scripts\python.exe v05\pipeline\build_spatial_v04.py
venv\Scripts\python.exe v05\pipeline\derive_regional_inflow_v04.py
venv\Scripts\python.exe v05\pipeline\derive_recommendations_v04.py
venv\Scripts\python.exe v05\pipeline\derive_regional_review_supply_v04.py
```

공간 Parquet가 이미 있으면 `build_spatial_v04.py`는 덮어쓰지 않고 중단한다.
재생성이 승인된 경우에만 `--overwrite`를 사용한다. 음식점 추천 전체 실행은 현재
환경에서 약 174초가 걸렸다.

## 5. DB 스키마와 적재

대상은 기존 MySQL `yelp_data`다. 새 DB를 만들지 않는다.

공간 테이블:

- `reviewer_spatial_summary`
- `vw_reviewer_regional_radius`

v05 파생 테이블:

- `reviewer_restaurant_recommendation`
- `reviewer_region_history`
- `regional_newcomer`
- `regional_review_supply`

운영 데이터 테이블:

- `retention_decisions` — 리뷰어별 현재 판단·메모·담당자·스누즈
- `retention_decision_history` — 생성·수정·삭제 감사 이력
- `retention_interactions` — 접촉 채널·시점·메모
- `target_lists` / `target_list_members` — 플레이북 대상 명단(F-5)

적재 명령:

```powershell
venv\Scripts\python.exe v05\database\load\load_spatial_v04.py --confirm-database yelp_data
venv\Scripts\python.exe v05\database\load\load_v05_derived.py --confirm-database yelp_data
```

두 로더 모두 실제 연결된 DB 이름을 확인한다. 파생 로더는 네 Parquet의 컬럼,
키 NULL, 중복, `model_version`을 사전 검사하고 하나의 트랜잭션에서 적재한다.
해당 모델 버전의 행이 이미 있으면 추가 적재하지 않고 실패한다. 자동 삭제나
자동 재적재는 제공하지 않는다.

운영 테이블은 별도 DDL을 적용한다. 기존 `database/` 파일과
`operator_decisions` 테이블은 변경하지 않는다.

```powershell
mysql --default-character-set=utf8mb4 yelp_data `
  -e "source v05/database/ddl/014_create_retention_operation_tables.sql"
mysql --default-character-set=utf8mb4 yelp_data `
  -e "source v05/database/ddl/015_create_target_list_tables.sql"
```

2026-07-31 로컬 `yelp_data` 적용 결과:

| 테이블 | 행 수 |
|---|---:|
| `reviewer_spatial_summary` | 11,374 |
| `reviewer_restaurant_recommendation` | 19,351 |
| `reviewer_region_history` | 37,953 |
| `regional_newcomer` | 126 |
| `regional_review_supply` | 140 |
| `retention_decisions` | 운영 중 누적 |
| `retention_decision_history` | append-only 누적 |
| `retention_interactions` | 운영 중 누적 |
| `target_lists` / `target_list_members` | 운영 중 누적 |

## 6. 적재 검증

적재 후 `v05/database/validation/validate_v05_derived.sql`을 MySQL Workbench 또는
승인된 SQL 실행 도구에서 실행한다. 반환되는 모든 `issue_count`가 0이어야 한다.

검증 범위:

- Parquet와 DB 행 수 일치
- 추천 리뷰어당 최대 3곳, 음식점 중복 없음
- 추천 거리·평점·리뷰 수 계약
- 추천 및 권역 이력의 코호트 외래키
- 2018 권역 매핑과 기존 `reviewer_region` 일치
- 신규 진입 전체 합계 23,524명
- 2018 이후 리뷰 공급 데이터 없음
- 14개 권역 및 2018 리뷰 610,672건 일치

2026-07-31 로컬 검증에서는 모든 항목이 0건이었다.

운영 데이터 검증은 다음 파일을 별도로 실행하며 모든 `issue_count`가 0이어야 한다.

```powershell
mysql --default-character-set=utf8mb4 yelp_data `
  -e "source v05/database/validation/validate_retention_operations.sql"
mysql --default-character-set=utf8mb4 yelp_data `
  -e "source v05/database/validation/validate_target_lists.sql"
```

## 7. API와 React 연결

| API | 용도 |
|---|---|
| `GET /api/reviewer-details/{user_id}/radius` | Reviewer 360 활동 반경 |
| `GET /api/reviewer-details/{user_id}/recommendations` | 플레이북 음식점 후보 |
| `GET /api/regional/radius` | 권역별 P90 반경 분포 |
| `GET /api/regional/derived-context?selection_year=2018` | 리뷰 공급 변화·신규 유입 |
| `GET /api/retention/decisions` | 모델 버전별 현재 관리자 판단 |
| `PUT/DELETE /api/retention/decisions/{reviewer_user_id}` | 판단·메모·스누즈 저장·삭제 |
| `GET /api/retention/decisions/{reviewer_user_id}/history` | 감사 이력 조회 |
| `GET/POST /api/retention/reviewers/{reviewer_user_id}/interactions` | 접촉 이력 조회·추가 |
| `GET /api/retention/target-lists` | 대상 명단 전체 조회 |
| `POST /api/retention/target-lists` | 대상 명단 생성(중복 제거) |
| `DELETE /api/retention/target-lists/{list_id}` | 대상 명단 삭제 |

선택적 v05 테이블이 없으면 추천·권역 파생 API는 HTTP 오류 대신
`available: false`, `reason: database_not_loaded`를 반환한다. React는 이때 추천
카드와 리뷰 공급 변화 탭을 숨겨 기존 화면을 유지한다.

### 로그인·회원가입 연동 경계

현재 브랜치에는 팀원의 로그인·회원가입 구현이 아직 병합되지 않았다. 그 전까지
`api/auth_context.py`가 서버 환경변수의 로컬 개발 운영자 식별자를 사용한다.
요청 본문에서 감사 이력의 사용자를 지정할 수는 없다.

인증 구현이 병합되면 다음 두 지점만 연결한다.

1. `api/auth_context.py`의 `get_current_operator()`에서 세션 또는 JWT를 검증하고
   불변 사용자 ID를 `subject`로 반환한다.
2. `app/src/services/decisionService.js`에서 팀 인증 방식에 맞춰 쿠키 또는
   Authorization 헤더를 전달한다. 현재도 세션 쿠키용 `credentials: include`는 켜져 있다.

로그인 계정 테이블을 v05에서 중복 생성하지 않는다. `assignee_subject`는 인증 사용자의
불변 ID를 받을 준비만 되어 있으며 담당자 선택 UI는 사용자 목록 API가 병합된 뒤
활성화한다.

## 8. 재적재와 롤백 주의

- 기존 v04 원본·코호트·모델 테이블은 수정하거나 삭제하지 않는다.
- 재적재가 필요하면 대상 모델 버전의 현재 행 수와 외래키 영향을 먼저 확인한다.
- 삭제·재적재는 DB 담당자 승인 후 트랜잭션으로 수행한다.
- `load_v05_derived.py`는 기존 행을 임의로 덮어쓰지 않는다.
- 서버 적용 전 로컬과 서버의 `database/.env` 대상이 다른지 반드시 확인한다.

## 9. 관련 문서

- [`docs/ui/V05_WORK_SPEC.md`](../docs/ui/V05_WORK_SPEC.md)
- [`docs/ui/V05_IMPLEMENTATION_REPORT.md`](../docs/ui/V05_IMPLEMENTATION_REPORT.md)
- [`docs/CODEX_HANDOFF.md`](../docs/CODEX_HANDOFF.md)
