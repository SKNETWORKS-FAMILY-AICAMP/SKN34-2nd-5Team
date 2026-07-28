# Yelp Reviewer Retention MySQL

실제 v04 코호트·피처·예측·평가 산출물을 MySQL에 적재하고 운영 큐와
관리자 판단 이력을 제공한다. 데모·합성 데이터는 사용하지 않는다.

v02·v03은 Trust Center 비교에 필요한 실제 평가 리포트만 같은 DB에
버전별로 적재한다. 두 버전의 과거 코호트나 모델 바이너리가 없는 상태를
숨기지 않으며, 리포트 전용 버전으로 명시한다.

## 1. 적재 원본

프로젝트 표준 경로의 다음 파일을 사용한다.

```text
data/interim/rolling/culinary_rolling_cohort_master_v04.parquet
data/processed/modeling_dataset_rolling_v04.parquet
data/processed/predictions/final_test_retention_profiles_v04.parquet
models/final_core_logistic_multiclass_v04.joblib
models/final_core_logistic_multiclass_metadata_v04.json
reports/tables/multiclass_validation_results_v04.csv
reports/tables/multiclass_top_k_performance_v04.csv
reports/tables/multiclass_confusion_matrix_v04.csv
reports/tables/final_feature_importance_v04.csv
reports/tables/final_feature_group_importance_v04.csv
data/processed/reviewer_region_v04.parquet
data/processed/reviewer_monthly_activity_v04.parquet
```

데이터와 모델은 `.gitignore` 대상이다. 새 환경에서는 팀의 v04 산출물
묶음을 별도로 전달받아 동일 경로에 배치한다.

권역·월별 활동 파일은 원본 리뷰와 음식점 Parquet을 준비한 뒤 생성한다.

```powershell
.\.venv\Scripts\python.exe pipeline\v04\derived_reviewer_activity.py
```

## 2. DBeaver에서 개발 DB 생성

`database/ddl/000_create_database.sql`을 DBeaver SQL Editor에서 실행한다.

```sql
CREATE DATABASE IF NOT EXISTS yelp_retention_v04_dev
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

시스템 DB나 다른 실습 DB를 삭제하지 않는다.

## 3. DB 적재 환경

프로젝트 가상환경에서 DB 전용 의존성을 설치한다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r database\requirements-db.txt
```

`.env.example`을 `.env`로 복사하고 로컬 접속정보를 입력한다.
`.env`는 Git에 포함하지 않는다.

```text
DB_HOST=localhost
DB_PORT=3306
DB_NAME=yelp_retention_v04_dev
DB_USER=root
DB_PASSWORD=개인_로컬_비밀번호
DB_CHARSET=utf8mb4
```

## 4. DB 변경 없는 원본 검증

DB 패키지를 설치하지 않아도 프로젝트의 pandas·pyarrow 환경에서 실행할 수
있다.

```powershell
.\.venv\Scripts\python.exe database\load\load_v04.py --dry-run
```

검증 항목:

- 모델 SHA256과 metadata 일치
- 전체 코호트·모델링 데이터 37,953행
- 최종 Test 프로필 6,533행
- Core 피처 43개
- sample_id 고유성
- 무한값 0개
- Test 유지·약화·중단 분포
- Top 20% 1,307명
- 평가 CSV와 metadata 일치
- 리뷰어 권역 6,533행과 코호트 참조 무결성
- 월별 활동의 관찰 구간 제한과 프로필 리뷰 수 합계 일치

## 5. 최초 스키마 생성과 실데이터 적재

아래 명령은 연결된 DB 이름이 확인값과 정확히 일치할 때만 실행된다.

```powershell
.\.venv\Scripts\python.exe database\load\load_v04.py `
  --apply-schema `
  --confirm-database yelp_retention_v04_dev
```

안전 원칙:

- `DROP`, `TRUNCATE`, 자동 삭제를 실행하지 않는다.
- 대상 DB 이름이 다르면 중단한다.
- 동일한 `v04` 데이터가 이미 있으면 덮어쓰지 않고 중단한다.
- 데이터 적재는 하나의 트랜잭션으로 처리한다.
- DDL은 최초 실행을 전제로 한다.

## 6. 적재 후 검증

DBeaver에서 다음 파일을 전체 스크립트로 실행한다.

```text
database/validation/validate_v04.sql
```

검증 파일은 특정 DB를 강제로 선택하지 않는다. 실행 전에 DBeaver에서 대상
DB를 선택하고 `SELECT DATABASE()` 결과가 의도한 이름인지 확인한다.

주요 기대값:

| 항목 | 값 |
|---|---:|
| cohort_samples | 37,953 |
| reviewer_features | 37,953 |
| validation_outcomes | 37,953 |
| model_predictions | 6,533 |
| reviewer_region | 6,533 |
| CRM 대상 | 1,307 |
| 유지·약화·중단 | 2,584 / 3,065 / 884 |
| 비교 활동 없음 | 1,692 |

## 7. 운영 View

`vw_reviewer_work_queue`는 운영 시점에 사용할 수 있는 정보만 노출한다.
2019년 실제 결과는 포함하지 않는다.

`vw_reviewer_validation`은 사후 검증이 필요할 때만 사용한다.

`vw_model_top20_summary`는 실제 Top 20% 포착 인원을 집계한다.

`vw_regional_risk_summary`는 리뷰어 단위 권역과 모델 예측을 결합해
권역별 유지·약화·중단, 고위험 비율, CRM 대상 수와 대표 도시를 집계한다.

## 8. v02·v03 Trust Center 비교 지표 적재

먼저 DB 변경 없이 두 리포트 묶음의 계약을 검증한다.

```powershell
.\.venv\Scripts\python.exe database\load\load_v03.py --dry-run
.\.venv\Scripts\python.exe database\load\load_v02.py --dry-run
```

v04가 들어 있는 동일 개발 DB에 버전별로 이어서 적재할 수 있다.

```powershell
.\.venv\Scripts\python.exe database\load\load_v03.py `
  --apply-schema `
  --confirm-database yelp_retention_v04_derived_dev

.\.venv\Scripts\python.exe database\load\load_v02.py `
  --apply-schema `
  --confirm-database yelp_retention_v04_derived_dev
```

적재 후 `database/validation/validate_historical_metrics.sql`을 실행한다.
세부 정규화 규칙은
`database/docs/HISTORICAL_MODEL_METRICS_CONTRACT.md`에 기록한다.

v03 다중분류 지표는 기존 평가 테이블을 재사용한다. v02 이진 검증과
Top-K만 각각 `model_binary_validation_metrics`,
`model_binary_topk_metrics`에 저장하고, 혼동행렬과 피처 중요도는 기존
테이블을 재사용한다.

## 9. 모델 파일

`joblib`은 DB 적재 과정에서 역직렬화하거나 실행하지 않는다. 파일 SHA256만
metadata와 대조하고 `model_versions`에 기록한다. 신규 예측 서비스가 별도로
승인될 때만 모델 추론 코드에서 사용한다.

v02·v03 모델 바이너리는 저장소에 없으므로 해당 버전의 `model_sha256`은
NULL이다. 대신 비교 리포트 파일별 SHA256과 리포트 묶음 계약 SHA256을
`metadata_json`에 저장한다.
