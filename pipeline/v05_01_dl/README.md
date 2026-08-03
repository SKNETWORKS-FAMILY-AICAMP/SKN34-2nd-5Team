# v05_01_dl 딥러닝 Challenger

기존 v04 연간 코호트와 Core 43 피처를 그대로 사용하는 독립 딥러닝
실험 경로다. 승인된 v04 머신러닝 모델과 데이터는 수정하지 않는다.

## 실행

프로젝트 루트에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dl.txt
.\.venv\Scripts\python.exe pipeline\v05_01_dl\train.py
```

## 산출물

- 모델: `models/experiments/v05_01_dl/`
- 평가 보고서: `reports/experiments/v05_01_dl/`
- 최종 Test 프로필:
  `data/processed/experiments/final_test_retention_profiles_v05_01_dl.parquet`

모델 점수는 보정된 실제 확률이 아니라 위험 순위 산정을 위한 점수다.

## 버전 규칙

- `v05_01_dl`: Core 43 기반 첫 딥러닝 challenger
- 후속 실험: `v05_02_dl`, `v05_03_dl` 순서로 생성
- 폴더 버전은 모델 실험 버전이며, 사용 데이터 버전은 메타데이터의
  `dataset_version`으로 별도 관리
