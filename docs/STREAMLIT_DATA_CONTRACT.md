# Streamlit 데이터 계약

Reviewer Retention Console이 읽는 데이터 산출물과 최소 컬럼을 정의한다.
팀 회의 후 파일을 추가하더라도 이 계약을 유지하면 화면 코드를 다시 만들 필요가 없다.

## 1. v03 필수 산출물

### 3클래스 리뷰어 리텐션 프로필

경로:

```text
data/processed/predictions/final_test_retention_profiles_v03.parquet
```

최소 필수 컬럼:

| 컬럼 | 의미 |
|---|---|
| `user_id` | 리뷰어 식별자 |
| `retained_score` | 확률 보정 전 유지 클래스 모델 점수 |
| `weakened_score` | 확률 보정 전 약화 클래스 모델 점수 |
| `stopped_score` | 확률 보정 전 중단 클래스 모델 점수 |
| `priority_score` | `weakened_score + stopped_score` 통합 우선순위 점수 |
| `predicted_state` | 임계값 정책에 따른 모델 판단 코드 0·1·2 |
| `priority_rank` | 통합 우선순위 |
| `priority_top_percent` | 통합 순위 상위 비율, 0~100 |
| `selected_for_crm` | 통합 상위 20% 검토 대상 여부, 0/1 |

권장 컬럼:

| 컬럼 | 의미 |
|---|---|
| `sample_id` | 사용자-선정연도 표본 식별자 |
| `selection_year` | 파워 리뷰어 선정연도 |
| `target_year` | 이탈 정답 연도 |
| `predicted_state_label` | 파워 지위 유지·약화·리뷰 활동 중단 |
| `retention_state` | 검증용 실제 상태 코드 0·1·2 |
| `retention_state_label` | 검증용 실제 상태 표현 |
| `churn` | 기존 이진 검증 라벨, 중단 상태와 동일 |
| `baseline_review_count` | 선정 기간 리뷰 수 |
| `recent_review_count` | 최근 관찰 기간 리뷰 수 |
| `review_count_decline_rate` | 리뷰 수 감소율 |
| `baseline_active_months` | 선정 기간 활동 월 수 |
| `recent_active_months` | 최근 관찰 기간 활동 월 수 |
| `active_month_decline_rate` | 활동 월 감소율 |
| `baseline_unique_business_count` | 선정 기간 고유 음식점 수 |
| `recent_unique_business_count` | 최근 고유 음식점 수 |
| `unique_business_decline_rate` | 고유 음식점 감소율 |
| `baseline_recency_days` | 선정 기간 말 기준 리뷰 공백 |
| `recent_recency_days` | 최근 관찰 기간 말 기준 리뷰 공백 |
| `recency_increase_days` | 리뷰 공백 증가일 |
| `baseline_mean_interval_days` | 선정 기간 평균 작성 간격 |
| `recent_mean_interval_days` | 최근 평균 작성 간격 |
| `mean_interval_increase_days` | 평균 작성 간격 증가일 |

`retention_state`, `retention_state_label`, `churn`,
`target_review_count`, `target_active_months`는 운영 기본 화면에서 숨기고
사용자가 검증 모드를 명시적으로 켠 경우에만 표시한다.

앱은 하위 페이지 호환을 위해 `priority_score`, `priority_rank`,
`priority_top_percent`, `selected_for_crm`을 각각 기존
`risk_score`, `risk_rank`, `risk_top_percent`, `crm_target` 별칭으로
내부 정규화할 수 있다. 이 별칭은 v02 위험 등급 정책을 v03 정책으로
확정하는 근거가 아니다.

## 2. v03 보고서 산출물

```text
reports/tables/
├─ retention_state_distribution_v03.csv
├─ multiclass_validation_results_v03.csv
├─ multiclass_top_k_performance_v03.csv
└─ multiclass_confusion_matrix_v03.csv

models/
├─ final_core_logistic_multiclass_v03.joblib
└─ final_core_logistic_multiclass_metadata_v03.json
```

통합 상위 20% 정책 집계는 프로필의 `selected_for_crm`과
`retention_state`로 재계산할 수 있다. 클래스별 5-Fold 성능과 혼동행렬은
보고서 파일이 없으면 임의로 만들지 않고 해당 신뢰 센터 영역을
`데이터 연결 필요`로 표시한다.

기존 v02 이진 모델과 Top 20% 파일은 비교 기준으로 보존한다. v03 운영
화면의 기본 수치로 혼합하지 않는다.

## 3. 1차 고도화 산출물

### 월별 리뷰어 활동

권장 경로:

```text
data/processed/predictions/reviewer_monthly_activity_v01.parquet
```

| 컬럼 | 필수 | 의미 |
|---|---|---|
| `user_id` | 필수 | 리뷰어 식별자 |
| `year_month` | 필수 | 활동 월 |
| `review_count` | 필수 | 월별 음식 관련 리뷰 수 |
| `active_business_count` | 선택 | 월별 고유 음식점 수 |
| `new_business_count` | 선택 | 월별 신규 음식점 수 |
| `average_rating` | 선택 | 월별 평균 평점 |

앱에서 500만 건 리뷰 원본을 직접 읽지 않고 사전 집계 파일을 사용한다.

### 지역 콘텐츠 위험

권장 경로:

```text
reports/tables/regional_risk_summary_v01.csv
```

| 컬럼 | 필수 | 의미 |
|---|---|---|
| `region` | 필수 | 대표 리뷰 활동 city 또는 state |
| `reviewers` | 필수 | 지역별 활동 리뷰어 수 |
| `high_risk_users` | 필수 | 긴급·집중 관리 리뷰어 수 |
| `high_risk_rate` | 필수 | 고위험 리뷰어 비율, 0~1 |
| `mean_risk_score` | 필수 | 평균 위험 점수 |
| `review_supply_change` | 선택 | 최근 리뷰 생산량 변화 |

지역은 거주지나 실제 생활권이 아니라 `대표 리뷰 활동 지역`으로 정의한다.

## 4. 실행 모드

| 모드 | 조건 | 화면 표시 |
|---|---|---|
| Project | v03 프로필과 핵심 v03 보고서 연결 | `PROJECT · v03` |
| Hybrid | v03 프로필만 연결되거나 일부 보고서 누락 | `HYBRID · v03` |
| Demo | v03 프로필 파일 없음 | `DEMO · v03` |

데모 데이터는 v03 Test 집계 수치와 동일한 익명 합성 리뷰어로 구성되며
실제 사용자 ID를 포함하지 않는다. 프로젝트 프로필이 연결되면 실제
프로젝트 데이터를 우선 사용한다.

## 5. 표현 제한

- 클래스 점수와 `priority_score`를 실제 상태 확률로 표시하지 않는다.
- `retention_state`와 `churn`은 분석 검증 모드에서만 표시한다.
- 모델 판단은 상태 확정이나 자동 혜택·제재 결정으로 표현하지 않는다.
- 지역별 수치가 없으면 가짜 지역 데이터를 만들지 않는다.
- 캠페인 발송·참여·복귀 데이터가 없으면 실행 버튼을 활성화하지 않는다.
