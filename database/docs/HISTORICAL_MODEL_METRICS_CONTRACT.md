# v02·v03 Trust Center 비교 지표 DB 계약

## 목적

v04 운영 데이터와 별도로 보존된 v02·v03 리포트 CSV를 같은 DB에
버전별로 누적해 Trust Center의 모델 비교 조회에 사용한다.

이 적재는 과거 모델을 재학습하거나 예측 프로필을 복원하지 않는다.
저장소에 실제로 존재하는 평가·중요도 리포트만 적재한다.

## 버전 등록

`model_versions`에는 v02와 v03을 `artifact_scope =
trust_center_metrics_only`로 등록한다.

저장소에는 두 버전의 모델 바이너리가 없으므로 `model_sha256`은 NULL이다.
리포트 파일별 SHA256과 전체 리포트 묶음의 계약 SHA256은
`metadata_json`에 저장한다. 리포트 해시를 모델 해시로 표시하지 않는다.

## v03

v03은 다중분류이므로 다음 기존 테이블을 재사용한다.

| 원본 | 대상 |
|---|---|
| `multiclass_validation_results_v03.csv` | `model_validation_metrics` |
| `multiclass_top_k_performance_v03.csv` | `model_topk_metrics` |
| `multiclass_confusion_matrix_v03.csv` | `model_confusion_matrix` |
| `final_feature_importance_v03.csv` | `feature_importance` |
| `final_feature_group_importance_v03.csv` | `feature_group_importance` |

혼동행렬의 `decision_policy`는 원본 전체가 `threshold`인지 검증한 뒤
공용 테이블에서는 제외한다. 다른 정책이 섞이면 적재를 중단한다.

개별 중요도에는 최종 Test Macro PR-AUC, 평가 지표, 방법, 반복 횟수를
원본 모델링 계약에 따라 보강한다. 그룹 중요도는 1회 그룹 제거 재학습
결과라 원본 `importance_std` NULL을 그대로 보존한다.

## v02

v02는 이진분류이므로 다중분류 검증·Top-K 열에 억지로 맞추지 않는다.

| 원본 | 대상 |
|---|---|
| Validation 및 Test 이진 평가 | `model_binary_validation_metrics` |
| Validation 및 Test 이진 Top-K | `model_binary_topk_metrics` |
| Validation 및 Test TN/FP/FN/TP | `model_confusion_matrix` |
| `final_feature_importance_v02.csv` | `feature_importance` |
| `final_feature_group_importance_v02.csv` | `feature_group_importance` |

혼동행렬 상태는 `active`와 `stopped`로 저장한다. 이진 중요도의 지표는
PR-AUC이며 개별 피처는 10회 단일 피처 순열, 그룹은 10회 공동 순열
결과다.

## 안전 조건

- 모든 PK는 `model_version`으로 시작해 v04와 섞이지 않는다.
- 대상 버전 데이터가 한 행이라도 있으면 자동 삭제·덮어쓰기 없이 중단한다.
- DB 이름은 `--confirm-database`와 실제 연결명이 정확히 같아야 한다.
- 한 버전의 모든 행은 하나의 트랜잭션으로 적재한다.
- 모델 바이너리나 프로필이 없다는 사실을 숨기지 않는다.
