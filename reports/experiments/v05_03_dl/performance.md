# v05_03_dl Core43 + Monthly24 GRU

- 파워 리뷰어·유지/약화/중단 정의와 v04 시간 분할을 유지했다.
- Core 43 정적 피처와 Y-1~Y 24개월 활동 시퀀스를 결합했다.
- Y+1 정보는 정답 생성과 최종 평가에만 사용했다.
- OOF Macro F1: 0.5695
- OOF Macro PR-AUC: 0.5939
- Test Macro F1: 0.5681
- Test Macro PR-AUC: 0.5951
- 유지 Recall: 56.31%
- 약화 Recall: 72.66%
- 중단 Recall: 38.35%
- Top 20% Precision/Recall/Lift:
  88.37% /
  29.25% /
  1.46×
- Seed Macro F1 표준편차: 0.0014

클래스 점수는 보정된 실제 확률이 아니라 위험 순위용 모델 점수다.
