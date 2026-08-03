# v05_04 딥러닝 피처 빌드

`modeling_dataset_rolling_v05_2.parquet`의 Core43·추가 9개 피처를 보존하면서
딥러닝 실험용 피처 세트와 수치적으로 안정적인 대안 피처를 생성한다.

## 입력

- `data/processed/modeling_dataset_rolling_v04.parquet`
- `data/processed/modeling_dataset_rolling_v05_2.parquet`
- `data/processed/experiments/monthly_sequence_v04_v05_03_dl.parquet`
- `models/final_core_logistic_multiclass_metadata_v04.json`

## 실행

```powershell
python pipeline\v05_04_dl_features\build_features.py
```

같은 산출물을 검증 후 다시 만들려면 `--overwrite`를 사용한다.

## 산출물

- 데이터:
  `data/processed/experiments/modeling_dataset_v05_2_dl_features_v05_04.parquet`
- 피처 세트:
  `reports/experiments/v05_04_dl_features/feature_sets.json`
- 피처 검증:
  `reports/experiments/v05_04_dl_features/feature_validation.csv`
- 빌드 메타데이터:
  `reports/experiments/v05_04_dl_features/feature_build_metadata.json`

## 원칙

- 원본 64컬럼 Parquet은 수정하지 않는다.
- 전역 결측치 대치·Scaling을 수행하지 않는다. 학습 Fold 내부에서만 적합한다.
- 메타데이터 12개와 정답 파생 컬럼은 모델 입력에서 제외한다.
- 피처 세트 선택은 expanding-time pooled OOF 결과만 사용한다.
- 최종 Test의 클래스·중요도를 피처 선택에 사용하지 않는다.

`core52_all_supplied`는 팀원이 제공한 52개 피처를 그대로 사용한다.
`core56_dl_stable`은 큰 값이 발생하는 최근 3개월 원시 비율과 Elite `-1`
센티널 대신 로그 비율·명시적 결측 표시 등 딥러닝용 대안을 사용하는 후보 세트다.
