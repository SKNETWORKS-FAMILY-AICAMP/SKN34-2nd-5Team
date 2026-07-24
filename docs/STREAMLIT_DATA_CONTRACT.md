# Streamlit 데이터 계약

Reviewer Retention Console이 읽는 데이터 산출물과 최소 컬럼을 정의한다.
팀 회의 후 파일을 추가하더라도 이 계약을 유지하면 화면 코드를 다시 만들 필요가 없다.

## 1. 현재 필수 산출물

### 리뷰어 위험 프로필

경로:

```text
data/processed/predictions/final_reviewer_risk_profiles_v02.parquet
```

최소 필수 컬럼:

| 컬럼 | 의미 |
|---|---|
| `user_id` | 리뷰어 식별자 |
| `risk_score` | 보정된 확률이 아닌 위험 순위 점수 |

권장 컬럼:

| 컬럼 | 의미 |
|---|---|
| `sample_id` | 사용자-선정연도 표본 식별자 |
| `selection_year` | 파워 리뷰어 선정연도 |
| `target_year` | 이탈 정답 연도 |
| `risk_rank` | 위험 순위 |
| `risk_top_percent` | 위험 상위 비율, 0~100 |
| `risk_percentile` | 위험 백분위, 0~100 |
| `risk_tier` | 긴급 관리·집중 관리·관찰 대상·일반 |
| `crm_target` | Top 20% 관리 대상 여부, 0/1 |
| `churn` | 검증용 실제 이탈 정답, 0/1 |
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

`risk_rank`, `risk_top_percent`, `risk_percentile`, `risk_tier`,
`crm_target`이 없으면 앱에서 `risk_score`를 기준으로 재계산한다.

## 2. 현재 보고서 산출물

```text
reports/tables/
├─ final_risk_tier_summary_v02.csv
├─ final_test_top_k_performance_v02.csv
├─ final_test_primary_policy_v02.csv
├─ validation_test_comparison_v02.csv
├─ final_feature_importance_v02.csv
├─ final_feature_group_importance_v02.csv
├─ feature_group_validation_results_v02.csv
└─ rolling_temporal_split_summary_v02.csv

models/
└─ final_core_hgb_metadata_v02.json
```

위험 등급 요약, Top 20% 정책, Top-K 파일이 없으면 앱이 리뷰어 위험
프로필에서 재계산한다. 모델 성능·피처 중요도·시간 분할 파일이 없으면
해당 신뢰 센터 영역만 안내 상태로 표시한다.

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
| Project | 핵심 프로젝트 산출물 연결 | 프로젝트 데이터 연결됨 |
| Hybrid | 위험 프로필만 연결되거나 일부 보고서 누락 | 일부 프로젝트 데이터 연결 |
| Demo | 위험 프로필 파일 없음 | 내장 데모 데이터 |

데모 데이터는 검증된 Test 집계 수치와 동일한 익명 합성 리뷰어로 구성된다.
실제 사용자 ID를 포함하지 않는다.

## 5. 표현 제한

- `risk_score`를 이탈 확률로 표시하지 않는다.
- `churn`은 분석 검증 모드에서만 사용자에게 표시한다.
- 지역별 수치가 없으면 가짜 지역 데이터를 만들지 않는다.
- 캠페인 발송·참여·복귀 데이터가 없으면 실행 버튼을 활성화하지 않는다.

