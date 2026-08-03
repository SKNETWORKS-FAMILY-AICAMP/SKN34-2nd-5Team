# v05_05 Lifecycle Fusion H2

`v05_05`는 원천 User 데이터에서 시점 안전하게 재구성한 Lifecycle 5개와
24개월 Core4 행동 시퀀스를 정보 성격에 맞게 분리 처리하는 개발 후보 모델이다.

```text
Core4 × 24개월 → GRU(hidden=64) ─────┐
                                      ├→ Risk head + conditional Stopped head
Lifecycle 5개 → MLP(hidden=16) ──────┘
```

## 시간 및 Test 보호 계약

- 개발 입력: selection year 2010~2017
- OOF 검증: selection year 2013~2017 expanding-time 5-Fold
- 개발·튜닝(피처 생성·학습·임계값 선택) 단계에서는 selection year 2018 행과
  target year 2019을 전혀 읽지 않는다
- 가중치와 임계값을 동결한 뒤에만 별도 경로([Test 평가](#test-평가)) 통해
  2018→2019 Test 1회 평가를 수행한다

2026-08-03 팀 합의로 Test 평가 경로를 추가했다. 학습·OOF 파이프라인(`build_features.py`,
`train.py`)은 여전히 2018 Test 입력을 읽지 않으며, Test 평가는 별도 스크립트
(`build_test_features.py`, `evaluate_test.py`)에서만 이뤄진다.

## Lifecycle 정의

- `account_age_days`: selection 연도 다음 해 1월 1일과 가입일의 일수 차이
- `elite_year_count_prior`: selection 연도보다 이전 Elite 연도 수
- `is_elite_selection_year`: selection 연도 Elite 여부
- `years_since_last_elite`: selection 시점까지 마지막 Elite 이후 경과연도, 이력 없음 `-1`
- `recent_elite_streak`: selection 연도에 끝나는 연속 Elite 기간

User JSON 스냅샷에 selection 이후 Elite 연도가 있더라도 모든 계산에서 제외한다.
누적 review count·반응·friends 같은 시점 불명확 User 스냅샷 값은 사용하지 않는다.

## 실행

```powershell
.\.venv\Scripts\python.exe pipeline\v05_05_dl\build_features.py `
  --user-json "C:\path\to\yelp_academic_dataset_user.json"

.\.venv\Scripts\python.exe pipeline\v05_05_dl\train.py
```

기존 산출물이 있을 때 의도적으로 다시 만들려면 `--overwrite`를 추가한다.

## Test 평가

`train.py`가 저장한 동결 가중치(`models/experiments/v05_05_dl/seed_*_state_dict.pt`)와
OOF에서 이미 정한 임계값을 그대로 사용해 2018→2019 Test 6,533건을 **딱 한 번** 평가한다.
Test 단계에서는 어떤 재학습이나 임계값 재탐색도 하지 않는다.

```powershell
.\.venv\Scripts\python.exe pipeline\v05_05_dl\build_test_features.py
.\.venv\Scripts\python.exe pipeline\v05_05_dl\evaluate_test.py
```

결과는 `reports/experiments/v05_05_dl/test_*`(지표·혼동행렬·Top-K·성능 요약)와
`data/processed/predictions/test_retention_profiles_v05_05_dl.parquet`(리뷰어별 예측 프로필,
v04의 `final_test_retention_profiles_v04.parquet`과 동일한 스키마)에 저장된다.

2026-08-03 Test 결과 요약([reports/experiments/v05_05_dl/test_performance.md](../../reports/experiments/v05_05_dl/test_performance.md)):

| 지표 | OOF | Test |
|---|---:|---:|
| Macro F1 | 0.5763 | 0.5731 |
| Macro PR-AUC | 0.5980 | 0.5962 |
| Weakened Recall | 66.76% | 67.86% |
| Stopped Recall | 43.25% | 37.56% |

Test와 OOF의 차이가 작아 과적합·누수 징후는 없다. 다만 v04 최종 Test(동일 2018→2019,
6,533건) 대비 Stopped Recall이 52.15% → 37.56%로 낮아, 이탈(stopped) 탐지가 중요한
화면에서는 v04 점수와 병기하거나 두 모델 비교를 거쳐야 한다. Macro F1(0.5521 → 0.5731),
Macro PR-AUC(0.5792 → 0.5962), Weakened Recall(58.37% → 67.86%)은 v05_05_dl이 우세하다.

MySQL 적재는 [`database/load/load_v05_05_dl.py`](../../database/load/load_v05_05_dl.py)를 쓴다.

## v05_05 내부 ablation

다음 실험은 모두 기준선 `v05_05_dl`에서 한 요소만 변경하고 동일한 시간 OOF와
3개 seed를 사용한다.

- `v05_05_01_dl`: State 전용 정적 피처 5개
- `v05_05_02_dl`: 최근 1·3·6개월 Last-K shortcut
- `v05_05_03_dl`: 신규 업체 탐색 중단 신호
- `v05_05_04_dl`: 조건부 stopped loss positive weight 1.5
- `v05_05_05_dl`: 위험군 세부 유형 Multi-task

```powershell
.\.venv\Scripts\python.exe pipeline\v05_05_dl\build_exploration_features.py
.\.venv\Scripts\python.exe pipeline\v05_05_dl\run_ablation.py --experiment v05_05_01_dl
```

나머지 실험은 `--experiment` 값만 변경한다. 어떤 ablation도 2018 Test 입력이나
2019 정답을 읽지 않는다.
