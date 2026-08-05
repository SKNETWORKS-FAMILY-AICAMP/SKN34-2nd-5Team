# 모델 파이프라인 안내

> **문서 상태: 현재 기준**
> 버전별 모델 실험의 관계와 재현 경로를 안내한다. 폴더명은 실험 이력과 산출물
> 계약이므로 임의로 변경하지 않는다.

## 버전 관계

| 버전 | 목적 | 상태 | 최종 모델 여부 | 결과 문서 |
|---|---|---|---|---|
| `v04` | 3클래스 Core 43 LogisticRegression 기준선과 공간·월별 파생 | 비교·롤백 기준 | 아니요 | [v04 성능](../reports/modeling/multiclass_model_performance_v04.md) |
| `v05_ml` | v04 코호트 기반 ML 후보 비교 | 비교 후보 | 아니요 | [XGBoost 성능](../reports/modeling/xgboost_multiclass_model_performance_v05.md) |
| `v05_01_dl` | Core 43 정적 피처 MLP Challenger | 실험 완료 | 아니요 | [결과](../reports/experiments/v05_01_dl/dl_core43_performance.md) |
| `v05_02_dl` | `extended81` 피처 확장 효과 비교 | 실험 완료 | 아니요 | [결과](../reports/experiments/v05_02_dl/performance.md) |
| `v05_03_dl` | Core 43 정적 피처와 24개월 월별 GRU 결합 | 실험 완료 | 아니요 | [결과](../reports/experiments/v05_03_dl/performance.md) |
| `v05_04_dl_features` | v05_04 계열 실험용 피처 생성 | 보조 파이프라인 | 아니요 | [설명](v05_04_dl_features/README.md) |
| `v05_04_dl` | 정적 피처·MLP·GRU Fusion 단계별 탐색 | 실험 완료 | 아니요 | [개발 요약](../reports/experiments/v05_04_04_dl/development_summary.md) |
| `v05_05_dl` | Core4 24개월 시퀀스와 Lifecycle 5개를 결합한 Lifecycle Fusion H2 | **최종 선정·운영 중** | **예** | [최종 학습 결과](../docs/02_reports/02_model_training_report.md) |
| `v05_06_dl` | GRU를 Multi-scale TCN으로 교체한 독립 후보 | 미채택 개발 후보 | 아니요 | [판정](../reports/experiments/v05_06_dl/decision.md) |

## 현재 재생성 경로

```powershell
python pipeline/v05_05_dl/train.py
python pipeline/v05_05_dl/evaluate_test.py
```

- 설정: `pipeline/v05_05_dl/config.json`
- 모델 산출물: `models/experiments/v05_05_dl/`
- Final Test 예측: `data/processed/predictions/test_retention_profiles_v05_05_dl.parquet`
- 평가 결과: `reports/experiments/v05_05_dl/`

모델·코호트·시간 분할을 변경할 때는 승인된 의사결정과
`configs/analysis_config_v04.yaml`을 먼저 확인한다.
