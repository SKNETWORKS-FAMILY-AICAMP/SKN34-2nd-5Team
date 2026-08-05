# 인공지능 학습 결과서 (Model Training Report)

**프로젝트명**: Yelp 파워 리뷰어 리텐션 상태 예측 (가입 고객 이탈 예측)  
**기타 정보**: [SKN34-2nd-5Team GitHub Repository](https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN34-2nd-5Team)  
**최종 선정 모델**: `v05_05_dl` (Lifecycle Fusion H2 Deep Learning Model)  
**작성일시**: 2026-08-04  

---

## 1. 평가 지표 체계 및 분석 목적

3-Class (`retained`, `weakened`, `stopped`) 상태 예측을 위해 다음과 같은 평가 지표 체계를 구축하였습니다.

| 평가 지표 | 분석 목적 및 의미 |
| :--- | :--- |
| **OOF Macro F1** | **[메인 평가 지표]** 3개 클래스의 분류 성능을 동일한 비중으로 통합 평가 |
| **OOF Macro PR-AUC** | 클래스 불균형 환경에서 전반적인 구분 및 위험 순위 산정 성능 평가 |
| **Weakened Recall** | 실제 활동 약화(위험 1단계) 리뷰어의 포착 비율 |
| **Stopped Recall** | 실제 활동 중단(완전 이탈) 리뷰어의 포착 비율 |
| **Precision@1000** | **[CRM 타겟팅 지표]** 위험 점수 상위 1,000명 중 실제 위험군(`weakened` + `stopped`) 비율 |
| **중증 오분류** | `retained`(유지) 고객을 `stopped`(이탈)로 잘못 분류한 치명적 오분류 건수 및 비율 |

---

## 2. 전체 모델 성능 비교 (ML vs DL)

동일한 OOF 검증 표본(24,596건, Expanding-time 5-Fold × 3 seeds)에서 수행된 전체 모델의 성과 비교입니다.

### 2.1 머신러닝 (v05_2 ML) 실험 결과

| 모델명 | 피처 세트 | OOF Macro F1 | 비고 |
| :--- | :--- | :---: | :--- |
| **XGBoost (ML 1위)** | Core45 (v05_2) | **0.566042** | ML 모델 중 성과 1위 (`test_macro_f1: 0.568396`) |
| **LightGBM** | Core45 (v05_2) | 0.566028 | XGBoost와 미세한 차이 |
| **Stacking** | ML Ensemble | 0.563623 | 단일 트리 모델 대비 성과 저하 |
| **Soft Voting** | ML Ensemble | 0.561799 | 앙상블 조합 성과 미흡 |
| **Logistic Regression** | Core45 (v05_2) | 0.561382 | 선형 모델 베이스라인 |
| **Random Forest** | Core45 (v05_2) | 0.557969 | 트리 베이스라인 |

### 2.2 딥러닝 (v05_01~v05_06 DL) 실험 결과

| 버전 | 입력 구조 | OOF Macro F1 | OOF Macro PR-AUC | Weakened Recall | Stopped Recall | Precision@1000 | 중증 오분류 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **v05_01_dl** | Core43 정적 MLP | 0.5597 | 0.5832 | 66.71% | 42.07% | - | - |
| **v05_02_dl** | Extended81 정적 MLP | 0.5581 | 0.5773 | 64.85% | 43.25% | - | - |
| **v05_03_dl** | Core43 + Monthly24 GRU | 0.5695 | 0.5939 | **69.31%** | 40.46% | - | - |
| **v05_04_04_dl** | Core56 Compact MLP | 0.5697 | 0.5902 | 66.63% | 43.06% | - | - |
| **v05_05_dl (최종)**| **월별 Core4 + Lifecycle 5개 (H2)** | **0.5763** | **0.5980** | 66.76% | 43.25% | **90.60%** | **538건 (2.19%)** |
| **v05_06_dl** | TCN + Lifecycle 5개 (H2) | 0.5751 | 0.5925 | 63.20% | **45.16%** | 90.04% | 650건 (2.64%) |

---

## 3. 최종 모델 선정 및 구조 명세: `v05_05_dl`

### 3.1 최종 모델 채택 사유
1. **후보 모델 중 가장 높은 OOF 성능**: OOF Macro F1 **`0.5763`**, OOF Macro PR-AUC **`0.5980`**으로 비교한 ML·DL 후보 중 가장 높은 값을 기록함.
2. **CRM 검토 큐 정밀도 (Precision@1000 = 90.60%)**:
   - 위험 점수 상위 1,000명 중 **906명이 실제 위험군(`weakened` 또는 `stopped`)**으로 확인되어 제한된 검토 인원을 우선순위화하는 근거로 사용할 수 있음.
3. **중증 오분류 수락 기준 충족 (2.19%)**:
   - `retained`를 `stopped`로 분류한 중증 오분류는 **538건(2.19%)**으로, 사전에 정한 OOF 수락 기준 2.5% 이하를 충족함.

### 3.2 `v05_05_dl (Lifecycle Fusion H2)` 아키텍처 구조
- **시계열 Branch**: 24개월간의 월별 리뷰 수, 활성 여부, 방문 업체 수, 평균 간격을 GRU(Hidden 64)로 인코딩하여 동적 활동 변화 추이 학습.
- **라이프사이클 Branch**: 파워리뷰어 연차, 과거 Elite 연도 수 등 5개 라이프사이클 특성을 MLP(Hidden 16)로 인코딩하여 유저 기반 성향 학습.
- **계층형 Head (Hierarchical H2 Head)**:
  - 1단계: 정상 유지(`retained`) vs 위험군(`at-risk`) 분류
  - 2단계: 위험군 내부에서 활동 약화(`weakened`) vs 활동 중단(`stopped`) 분류

### 3.3 최종 모델 테스트 결과

학습에 사용하지 않은 2018년 선정 코호트(6,533명, 2019년 상태 평가)에 대한 Final Test 결과입니다. 가중치와 임계값은 OOF 검증까지만 사용해 사전에 고정했으며, Test 평가 전 별도의 재조정을 하지 않았습니다.

| 평가 지표 (Metric) | Metric Score |
| --- | --- |
| Test Macro F1 | 0.5731 |
| Test Macro PR-AUC | 0.5962 |
| Weakened Recall | 0.6786 |
| Stopped Recall | 0.3756 |
| Precision@1000 | 0.8990 |

---

## 4. `v05_05_dl` 내부 Ablation Study 결과

`v05_05_dl` 기본 구조에 대한 내부 파이프라인 요소별 Ablation 실험 결과입니다.

| 실험 코드 | 실험 구성 및 변경 사항 | OOF Macro F1 | 비고 |
| :--- | :--- | :---: | :--- |
| **v05_05_dl (Base)** | **GRU + Lifecycle MLP + 계층형 H2 Head** | **0.5763** | **기본 메인 모델** |
| `v05_05_01` | 상태 정적 피처 5개 추가 | 0.5750 | -0.0013 소폭 하락 |
| `v05_05_02` | 최근 1·3·6개월 Shortcut 피처 추가 | 0.5749 | -0.0013 소폭 하락 |
| `v05_05_03` | 신규 업체 탐색 중단 신호 추가 | 0.5745 | -0.0018 소폭 하락 |
| `v05_05_04` | Stopped 클래스 손실 가중치 1.5 부여 | 0.5755 | -0.0008 소폭 하락 |
| `v05_05_05` | Weakened 하위유형 보조학습 추가 | 0.5765 | +0.0002 미세 상승하나 신뢰구간 0 포함 |

> **결론**: 복잡도를 늘린 파생 보조학습(`v05_05_05`) 대비 기본 `v05_05_dl` 구조가 과적합 없이 stopped 포착률, Precision@1000, 중증 오분류 지표에서 가장 균형 잡히고 안정적인 성능을 보임.

---

## 5. XAI(설명 가능성) 및 주요 신호 비즈니스 해석

`v05_05_dl`에 대한 Permutation Importance 등 변수별 정량 기여도 산출물은 아직 없어 Top10 변수 중요도 표는 제공하지 않습니다. 아래는 모델 구조와 평가 결과를 바탕으로 한 핵심 신호 해석입니다.

### 5.1 핵심 입력 신호와 운영 해석 (3줄 요약)
1. **월별 활동 시퀀스**: 모델은 최근 24개월의 월별 리뷰 수, 활동 여부, 방문 업체 수와 평균 작성 간격을 함께 입력받아 시간에 따른 활동 변화를 학습함. 변수별 기여도 순위는 별도 중요도 분석 전에는 단정하지 않음.
2. **라이프사이클 정보**: 과거 Elite 선정 연도 수와 최근 연속 유지 기간 등 5개 특성은 리뷰어의 활동 이력을 보완하는 입력으로 사용함. 각 특성의 독립적인 효과와 방향은 현재 평가 결과만으로 확정하지 않음.
3. **위험 상위 1,000명 검토**: OOF Precision@1000 90.60%는 제한된 운영 인력으로 우선 검토 대상을 정하는 근거다. 캠페인 효과와 ROI는 실제 실행·성과 데이터가 없으므로 별도 검증이 필요함.

---

## 6. 최종 모델 직렬화 및 파일 배포 구조

최종 모델은 단일 파일이 아니라 `models/experiments/v05_05_dl/` 아래의 3-seed 앙상블 산출물 묶음입니다(총 약 246KB). 이 폴더는 `.gitignore`로 관리되는 로컬 파이프라인 산출물이라 git에는 포함되지 않으며, 아래 재생성 절차로 다시 만들 수 있습니다.

- **모델 가중치 (3-seed 앙상블)**: `models/experiments/v05_05_dl/seed_42_state_dict.pt`, `seed_2026_state_dict.pt`, `seed_3405_state_dict.pt`
- **전처리 객체**: `models/experiments/v05_05_dl/preprocessing.joblib`
- **모델 메타데이터 JSON**: `models/experiments/v05_05_dl/metadata.json`
- **최종 CRM 타겟팅 예측 결과**: `data/processed/predictions/test_retention_profiles_v05_05_dl.parquet`
- **체크섬 (SHA-256, `reports/experiments/v05_05_dl/test_metrics.json`의 `model_artifacts` 기준)**:
  - `preprocessing.joblib`: `b22dc7360a989b03dae1801ffc1c9ac6776bf74e0329d600c6b7c635e6acea1f`
  - `seed_42_state_dict.pt`: `6f97cb1efee0821d6121beca6064b8ac66ddf99a39a5e992655691a53d20f0bb`
  - `seed_2026_state_dict.pt`: `852e264af18f299ab1e17f72fdc22dee3601f95d50dbdf86ba38d1cb6947767d`
  - `seed_3405_state_dict.pt`: `e4556b26924b2ca18b326481070abd95a56784ca323bb3d9510d42090290b8b3`
- **재생성 절차**: `pipeline/v05_05_dl/train.py` 실행 (seed·하이퍼파라미터는 `pipeline/v05_05_dl/config.json` 고정값 사용, 모델 구조는 `train.py`의 `LifecycleFusionH2` 클래스, 추론·앙상블 로직은 `pipeline/v05_05_dl/evaluate_test.py` 참고)
