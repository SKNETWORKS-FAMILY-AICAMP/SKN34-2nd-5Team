# v05_04 딥러닝 모델 개발 요약

## 범위

- 완료: 정적 피처 Ablation, 제한적 MLP 튜닝, GRU Fusion 비교,
  OOF 기준 최종 DL 후보 선정 및 최종 Test 평가
- 보류: `v05_04_05` 머신러닝 공정 비교, `v05_04_06` ML·DL 앙상블

모든 피처·구조·임계값 선택은 expanding-time pooled OOF만 사용했다.
최종 Test는 OOF 1위 후보 하나를 고정한 뒤 평가했다.

## v05_04_01 정적 피처 비교

| 순위 | 피처 세트 | 피처 수 | OOF Macro F1 | OOF Macro PR-AUC | Weakened Recall | Stopped Recall |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Core56 DL Stable | 56 | 0.5693 | 0.5894 | 67.76% | 41.94% |
| 2 | Filtered45 | 45 | 0.5687 | 0.5888 | 67.25% | 43.20% |
| 3 | Core52 전체 제공 피처 | 52 | 0.5679 | 0.5875 | 67.32% | 42.72% |
| 4 | Core43 | 43 | 0.5597 | 0.5832 | 66.71% | 42.07% |

신규 피처는 정적 MLP에서 Core43보다 높은 OOF 성능을 보였다. 원시 52개
전체보다 안정화·선별 피처 세트가 더 높았다.

## v05_04_02 MLP 튜닝

| 순위 | 피처 세트 | 모델 | OOF Macro F1 | OOF Macro PR-AUC |
|---:|---|---|---:|---:|
| 1 | Core56 DL Stable | Compact 128→64 | 0.5697 | 0.5902 |
| 2 | Core56 DL Stable | Reference 128→64→32 | 0.5693 | 0.5894 |
| 3 | Filtered45 | Reference 128→64→32 | 0.5687 | 0.5888 |

최종 정적 후보는 Core56 DL Stable과 Compact MLP다.

## v05_04_03 GRU Fusion

| 후보 | OOF Macro F1 | OOF Macro PR-AUC | Weakened Recall | Stopped Recall |
|---|---:|---:|---:|---:|
| 기존 v05_03 Core43 + GRU | 0.5695 | 0.5939 | 69.31% | 40.46% |
| Core56 DL Stable + GRU | 0.5685 | 0.5941 | 69.91% | 38.95% |

신규 피처는 정적 MLP에는 도움이 됐지만 기존 GRU와 결합했을 때 Macro F1을
높이지 못했다. 월간 시퀀스와 신규 Momentum 정적 피처의 정보 중복 가능성이 있다.

## v05_04_04 최종 DL 결과

OOF 기준 최종 순위는 다음과 같다.

1. Core56 DL Stable Compact MLP: 0.5697
2. 기존 v05_03 Core43 + GRU: 0.5695
3. Core56 DL Stable + GRU: 0.5685

따라서 Core56 DL Stable Compact MLP 하나만 최종 Test 평가했다.

| 지표 | v05_03 | v05_04 정적 MLP | 차이 |
|---|---:|---:|---:|
| OOF Macro F1 | 0.5695 | 0.5697 | +0.0003 |
| Test Macro F1 | 0.5681 | 0.5730 | +0.0049 |
| Test Macro PR-AUC | 0.5951 | 0.5944 | -0.0007 |
| Test Weakened Recall | 72.66% | 69.36% | -3.30%p |
| Test Stopped Recall | 38.35% | 40.27% | +1.92%p |
| Top20 Precision | 88.37% | 89.06% | +0.69%p |
| Top20 Recall | 29.25% | 29.48% | +0.23%p |
| Top20 Lift | 1.46 | 1.47 | +0.01 |

## 해석과 제한사항

- OOF Macro F1 우위는 약 0.00025로 작고, v05_04 정적 후보의 시드 표준편차
  0.00193보다 작다. 선정 규칙상 1위이지만 압도적인 개선으로 해석하지 않는다.
- v05_04는 stopped Recall과 Top20 운영 지표가 개선됐지만 weakened Recall과
  Macro PR-AUC는 소폭 하락했다.
- 팀원 제공 `inactive_month_count_3m/6m`과 기존 v05_03 월별 시퀀스 사이의
  부분 불일치는 피처 생성 코드로 원인을 확인해야 한다.
- 클래스 점수는 보정된 이탈 확률이 아니라 위험 순위 산정용 모델 점수다.
- 최종 운영 모델 결정은 동일 OOF·Test 계약의 머신러닝 결과와 사용자 단위
  예측 확률을 받은 뒤 비교·앙상블 단계에서 확정한다.
