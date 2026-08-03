# v05_01_dl 딥러닝 Core 43 비교 실험

## 실험 계약

- 기존 v04 연간 코호트, Core 43, 3클래스 라벨을 그대로 사용했다.
- 2013~2017 확장형 시간 5-Fold의 OOF에서 구조·가중치·임계값을 선택했다.
- 최종 학습은 선정연도 2010~2017, 최종 Test는 2018→2019다.
- Test는 후보 선택에 사용하지 않았다.
- 딥러닝 결과는 기존 v04를 대체하지 않는 challenger 산출물이다.
- 클래스 점수는 보정된 실제 확률이 아니라 위험 순위용 모델 점수다.

## 선택된 딥러닝 조건

- 후보: `mlp_medium_unweighted`
- 은닉층: `128 → 64 → 32`
- Dropout: 0.2
- Learning rate: 0.0007
- Weight decay: 0.0005
- Epochs: 50
- Batch size: 512
- 클래스 가중 손실: False
- 약화 임계값: 0.42
- 중단 임계값: 0.35
- 최종 모델: seed 42, 2026, 3405 점수 평균 앙상블

## 최종 Test 비교

| 후보 | Macro F1 | Macro PR-AUC | Balanced Acc. | 유지 Recall | 약화 Recall | 중단 Recall | Top20 Precision | Top20 Recall | Lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ML Logistic Core43 v04 | 0.5521 | 0.5792 | 56.49% | 58.94% | 58.37% | 52.15% | 87.38% | 28.92% | 1.45× |
| DL MLP Ensemble Core43 v05_01 | 0.5619 | 0.5845 | 55.20% | 56.54% | 70.38% | 38.69% | 88.06% | 29.15% | 1.46× |

## Seed 안정성

- 단일 seed Test Macro F1 평균: 0.5608
- 단일 seed Test Macro F1 표준편차: 0.0021
- 3-seed 앙상블 Test Macro F1: 0.5619

## 해석 원칙

운영 모델 승격은 Macro F1 하나가 아니라 PR-AUC, 클래스별 Recall,
Top 20% Lift, seed 안정성, 추론 비용과 설명 가능성을 함께 검토한다.
