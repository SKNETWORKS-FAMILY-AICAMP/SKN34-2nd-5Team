# 모델·실험 결과 안내

> **문서 상태: 현재 기준**
> `reports/`의 원본 실험 결과와 최종 공식 결과서의 관계를 안내한다.

## 폴더 구분

| 경로 | 역할 | 사용 기준 |
|---|---|---|
| `experiments/` | 버전별 학습·Ablation·후보 비교 원본 | 실험 재현과 후보 판정 |
| `modeling/` | v02~v05 모델 세대별 성능 요약 | 과거 모델 비교·롤백 |
| `tables/` | 혼동행렬, Top-K, 피처 중요도 등 정형 결과 | DB 적재·문서·검증 입력 |
| `figures/` | 모델링·검증 시각화 | 보고서와 발표 자료 |

## 현재 공식 결과

- 최종 선정 모델: `v05_05_dl` Lifecycle Fusion H2
- 최종 공식 결과서: [모델 학습 결과서](../docs/02_reports/02_model_training_report.md)
- 데이터 처리 기준: [데이터 전처리 결과서](../docs/02_reports/01_data_preprocessing_report.md)
- 배포·QA 판정: [모델 배포·테스트 결과서](../docs/02_reports/03_model_deployment_test_report.md)
- 상세 파이프라인 관계: [pipeline/README.md](../pipeline/README.md)

## 주요 버전 상태

| 결과 경로 | 상태 | 설명 |
|---|---|---|
| `experiments/v05_05_dl/` | 최종 기준 | OOF와 동결 후 Final Test 결과 |
| `experiments/v05_06_dl/` | 미채택 후보 | TCN 후보이며 `v05_05_dl`을 교체하지 않음 |
| `modeling/multiclass_model_performance_v04.md` | 비교·롤백 기준 | 이전 v04 운영 기본 모델 |
| `modeling/xgboost_multiclass_model_performance_v05.md` | 비교 후보 | Trust Center의 XGBoost 비교 모델 |

실험 결과를 삭제하거나 최신 결과로 덮어쓰지 않는다. 최종 여부는 폴더명이 아니라
공식 결과서와 파이프라인 색인의 상태를 기준으로 판단한다.
