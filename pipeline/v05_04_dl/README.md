# v05_04 딥러닝 모델 개발

팀원 산출물이 필요한 ML 비교·앙상블 전까지 딥러닝 모델 개발을 완료한다.

## 단계

1. `run_01_static_ablation.py`: 고정 MLP로 피처 세트 OOF 비교
2. `run_02_mlp_tuning.py`: 상위 피처 세트에서 제한적 MLP 튜닝
3. `run_03_gru_fusion.py`: 최고 신규 정적 피처와 기존 GRU 결합
4. `run_04_finalize.py`: OOF 1위 후보 하나를 선택한 후 최종 Test 평가

## 실행

프로젝트 루트에서 DL 가상환경을 사용한다.

```powershell
.\.venv\Scripts\python.exe pipeline\v05_04_dl\run_01_static_ablation.py
.\.venv\Scripts\python.exe pipeline\v05_04_dl\run_02_mlp_tuning.py
.\.venv\Scripts\python.exe pipeline\v05_04_dl\run_03_gru_fusion.py
.\.venv\Scripts\python.exe pipeline\v05_04_dl\run_04_finalize.py
```

모든 피처·모델·임계값 선택은 expanding-time pooled OOF만 사용한다.
`run_04_finalize.py`만 OOF 1위 후보의 최종 Test를 확인한다.

`v05_04_05` ML 공정 비교와 `v05_04_06` ML·DL 앙상블은 팀원 예측 파일을
받은 뒤 별도로 진행한다.
