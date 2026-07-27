# Streamlit 데이터 계약

Reviewer Retention Console이 읽는 v04 데이터 산출물과 운영 화면의 노출
범위를 정의한다.

## 1. v04 핵심 산출물 묶음

아래 다섯 파일은 동일한 모델 버전 묶음으로 로드한다.

```text
data/processed/predictions/final_test_retention_profiles_v04.parquet
models/final_core_logistic_multiclass_metadata_v04.json
reports/tables/multiclass_validation_results_v04.csv
reports/tables/multiclass_top_k_performance_v04.csv
reports/tables/multiclass_confusion_matrix_v04.csv
```

한 파일만 v03 또는 v02로 대체하지 않는다. 일부 파일만 존재하면 v04 핵심
묶음이 불완전한 것으로 처리한다.

메타데이터에서 확인할 기준:

- `version`: `v04`
- `test_selection_year`: 2018
- `test_target_year`: 2019
- `test_samples`: 6,533
- `feature_count`: 43
- `priority_policy.primary_target_rate`: 0.20

프로필의 시간 구조:

| 컬럼 | 의미 |
|---|---|
| `comparison_year` | 비교 연도, 2017 |
| `selection_year` | 파워 리뷰어 후보 선정 및 피처 마감 연도, 2018 |
| `target_year` | 실제 상태 검증 연도, 2019 |

## 2. v04 프로필 필수 컬럼

| 컬럼 | 의미 |
|---|---|
| `sample_id` | 사용자-선정연도 표본 식별자 |
| `user_id` | 리뷰어 식별자 |
| `comparison_year` | 비교 연도 |
| `selection_year` | 선정 및 피처 마감 연도 |
| `target_year` | 실제 상태 검증 연도 |
| `prior_activity_available` | 비교 연도 활동 존재 여부 |
| `retained_score` | 확률 보정 전 유지 클래스 점수 |
| `weakened_score` | 확률 보정 전 약화 클래스 점수 |
| `stopped_score` | 확률 보정 전 중단 클래스 점수 |
| `priority_score` | `weakened_score + stopped_score` |
| `predicted_state` | 모델 판단 코드 0·1·2 |
| `priority_rank` | 통합 우선순위 |
| `priority_top_percent` | 통합 순위 상위 비율 |
| `selected_for_crm` | 통합 상위 20% 검토 대상 여부 |

2017년 비교 활동이 없는 표본은 `prior_activity_available=0`이다. 해당 표본의
전년 대비 감소율 결측값을 0으로 대체하거나 `0% 감소`로 표현하지 않는다.

화면 표현:

```text
2017년 비교 활동 없음
전년도 대비 변화율 계산 불가
```

## 3. 검증 정답 분리

다음 컬럼은 모델 입력이 아니며 운영 기본 화면에서 노출하지 않는다.

```text
target_review_count
target_active_months
retention_state
retention_state_label
churn
```

`status_loss`, `actual_result`처럼 위 컬럼에서 파생된 값도 운영 CSV에 포함하지
않는다. Reviewer 360에서 사용자가 `검증 정답 표시`를 명시적으로 켠 경우에만
사후 검증 영역에서 표시한다.

## 4. v04 설명 산출물 묶음

```text
reports/tables/final_feature_importance_v04.csv
reports/tables/final_feature_group_importance_v04.csv
```

두 파일은 함께 로드한다. 하나가 누락되거나 메타데이터와 계약이 다르면 v03
결과로 대체하지 않고 피처 중요도 영역을 비활성화한다.

검증 조건:

- `model_version=v04`
- `split=final_test`
- 기준 Macro PR-AUC가 모델 메타데이터와 일치
- 개별 피처 43개가 메타데이터 `feature_columns`와 일치
- 그룹별 피처 수 합계 43개
- 개별 피처: `single_feature_permutation`, 20회
- 그룹: `joint_group_permutation`, 20회

중요도는 모델 선정이 아닌 사후 해석 전용이다. 값은 확률이나 영향 비율이
아니라 정보를 섞었을 때 감소한 Macro PR-AUC다.

### 4.1 v03 비교 전용 묶음

신뢰 센터에서 v04와 이전 3클래스 모델을 비교하기 위해 아래 다섯 파일을
별도 묶음으로 로드한다.

```text
reports/tables/multiclass_validation_results_v03.csv
reports/tables/multiclass_top_k_performance_v03.csv
reports/tables/multiclass_confusion_matrix_v03.csv
reports/tables/final_feature_importance_v03.csv
reports/tables/final_feature_group_importance_v03.csv
```

v03 묶음은 운영 기본값이나 v04 핵심 묶음의 대체 자료가 아니다. 다섯 파일이
모두 존재하고 검증 결과·혼동행렬·중요도의 표본 및 기준 지표가 일치할 때만
신뢰 센터의 접힌 비교 영역에 표시한다.

화면에서는 다음 시간 구조를 명시한다.

```text
2017년 후보 선정
2018년 활동 관찰
2019년 실제 상태 검증
```

v03 성능·Top-K·혼동행렬과 피처 중요도는 각각
`v03 비교 기준 (3클래스 이전 코호트, 참고용)` 영역에서 기본적으로 접힌
상태로 제공한다. v02 이진 모델 비교 영역도 별도로 유지한다.

## 5. 관리자 판단 키

관리자 판단은 `user_id` 단독이 아니라 다음 복합 키로 저장한다.

```text
model_version + sample_id
```

기존 v03 `user_id` 단독 키는 삭제하지 않지만 v04 판단으로 자동 승계하지
않는다.

Reviewer 360에서 플레이북으로 전달하는 값:

```text
sample_id
user_id
manager_decision
risk_type
model_judgment
priority_rank
priority_top_percent
priority_score
selected_for_crm
```

## 6. 지역 콘텐츠 위험

지역 콘텐츠 위험은 v04 모델 결과가 아니다.

권장 출처:

```text
reports/tables/regional_risk_summary_v01.csv
```

파일이 없으면 가짜 지역 수치를 생성하지 않고 `정의·데이터 필요` 상태를
유지한다. 지역은 거주지가 아니라 음식점 리뷰 활동 지역이다.

## 7. 실행 모드

| 모드 | 조건 |
|---|---|
| Project | v04 핵심 산출물 다섯 파일 연결 |
| Demo | v04 핵심 산출물 전체가 없으며 익명 합성 데모 사용 |

프로젝트 프로필이 하나라도 존재하는데 핵심 묶음이 불완전하면 다른 버전으로
대체하지 않고 명시적인 데이터 계약 오류를 표시한다.

## 8. 표현 제한

- 클래스 점수와 `priority_score`를 실제 상태 확률로 표시하지 않는다.
- 모델 판단을 자동 혜택·제재 결정으로 표현하지 않는다.
- 2019년 실제 결과를 운영 시점에 알 수 있었던 정보처럼 표시하지 않는다.
- 데이터가 없는 기능에 합성 운영 실적을 표시하지 않는다.
- CRM 발송·참여·복귀 데이터가 없으면 실행 버튼을 활성화하지 않는다.
