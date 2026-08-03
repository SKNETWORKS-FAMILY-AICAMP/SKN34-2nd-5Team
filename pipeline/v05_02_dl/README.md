# v05_02_dl 딥러닝 Challenger

승인된 v04 코호트와 시간 구조를 유지하면서 Core 43에 카테고리,
맛집 탐방 반경, 평점 변화 피처를 추가한 `extended81` 실험이다.

`v05_01_dl`과 동일한 MLP 구조·학습 조건을 사용해 피처 확장의 효과만
비교한다. Useful·Cool·Funny 반응과 타깃 연도 정보는 입력에서 제외한다.

## 실행

프로젝트 루트에서 순서대로 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dl.txt
.\.venv\Scripts\python.exe pipeline\v05_02_dl\build_features.py
.\.venv\Scripts\python.exe pipeline\v05_02_dl\train.py
```

확장 데이터셋을 다시 만들 때만 `--overwrite`를 사용한다.

```powershell
.\.venv\Scripts\python.exe pipeline\v05_02_dl\build_features.py --overwrite
```

## 산출물

- 확장 데이터:
  `data/processed/experiments/modeling_dataset_v04_extended81_v05_02_dl.parquet`
- 모델: `models/experiments/v05_02_dl/`
- 평가 보고서: `reports/experiments/v05_02_dl/`
- 최종 Test 프로필:
  `data/processed/experiments/final_test_retention_profiles_v05_02_dl.parquet`

모델 점수는 보정된 실제 확률이 아니라 위험 순위 산정을 위한 점수다.
