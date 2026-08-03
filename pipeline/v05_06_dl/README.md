# v05_06 Multi-scale TCN H2

`v05_06_dl`은 `v05_05_dl`의 피처·시간 분할·손실함수·임계값 탐색 조건을 고정하고,
GRU 시퀀스 인코더만 Multi-scale TCN으로 교체하는 독립 모델 계열 실험이다.

## 구조

```text
Core4 × 24개월
  → 1×1 projection + positional embedding
  → residual temporal conv blocks (dilation 1, 2, 4, 8)
  → attention pooling + recent-state shortcut
Lifecycle 5개 → MLP
  → fusion
  → Risk head + conditional Stopped head
```

## 평가 계약

- 개발 데이터: selection year 2010~2017
- OOF: selection year 2013~2017 expanding-time 5-Fold × 3 seeds
- 기준 모델: `v05_05_dl`, 동일 OOF sample 비교
- Final Test(selection year 2018 / target year 2019): 접근하지 않음
- 결과 점수는 보정 확률이 아니라 분류 및 위험 순위 산정용 모델 점수

## 실행

```powershell
.\.venv\Scripts\python.exe pipeline\v05_06_dl\train.py
```

기존 결과를 명시적으로 다시 만들 때만 `--overwrite`를 사용한다.
