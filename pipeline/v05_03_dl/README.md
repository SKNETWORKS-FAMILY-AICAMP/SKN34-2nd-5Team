# v05_03_dl Core43 + Monthly GRU

승인된 v04 코호트·라벨·시간 분할을 유지하고, Core 43 정적 피처와
비교연도 `Y-1`부터 선정연도 `Y`까지의 24개월 활동 흐름을 함께 학습한다.

월별 입력은 리뷰 수, 고유 음식점 수, 활동 여부이며 활동이 없는 달은
0으로 채운다. 타깃연도 `Y+1` 정보는 정답 생성과 평가에만 사용한다.

## 실행

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dl.txt
.\.venv\Scripts\python.exe pipeline\v05_03_dl\build_sequences.py
.\.venv\Scripts\python.exe pipeline\v05_03_dl\train.py
```

시퀀스를 다시 만들 때만 `--overwrite`를 사용한다.

## 산출물

- 월별 시퀀스:
  `data/processed/experiments/monthly_sequence_v04_v05_03_dl.parquet`
- 모델: `models/experiments/v05_03_dl/`
- 보고서: `reports/experiments/v05_03_dl/`
- 최종 Test 프로필:
  `data/processed/experiments/final_test_retention_profiles_v05_03_dl.parquet`
