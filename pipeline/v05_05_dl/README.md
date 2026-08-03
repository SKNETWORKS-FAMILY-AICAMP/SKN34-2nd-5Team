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
- selection year 2018 행: 피처 생성·학습·예측·평가에서 제외
- target year 2019: v05_05에서 접근하지 않음
- 결과물은 최종 승격 모델이 아니라 OOF 개발 후보

v05_05에는 새로운 Test 점수를 만들지 않는다. 팀 합의 전에는 Test 입력 생성 코드도 추가하지 않는다.

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
