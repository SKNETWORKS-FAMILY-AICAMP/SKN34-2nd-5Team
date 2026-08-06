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

최종 모델은 단일 파일이 아니라 `models/experiments/v05_05_dl/` 아래의 3-seed 앙상블 산출물 묶음입니다(총 약 246KB). 이 폴더는 `.gitignore`로 관리되는 로컬 파이프라인 산출물이라 git에는 포함되지 않으며, 아래 **모델 재생성 파이프라인 실행가이드**로 다시 만들 수 있습니다.

- **모델 가중치 (3-seed 앙상블)**: `models/experiments/v05_05_dl/seed_42_state_dict.pt`, `seed_2026_state_dict.pt`, `seed_3405_state_dict.pt`
- **전처리 객체**: `models/experiments/v05_05_dl/preprocessing.joblib`
- **모델 메타데이터 JSON**: `models/experiments/v05_05_dl/metadata.json`
- **최종 CRM 타겟팅 예측 결과**: `data/processed/predictions/test_retention_profiles_v05_05_dl.parquet`
- **체크섬 (SHA-256, `reports/experiments/v05_05_dl/test_metrics.json`의 `model_artifacts` 기준)**:
  - `preprocessing.joblib`: `b22dc7360a989b03dae1801ffc1c9ac6776bf74e0329d600c6b7c635e6acea1f`
  - `seed_42_state_dict.pt`: `6f97cb1efee0821d6121beca6064b8ac66ddf99a39a5e992655691a53d20f0bb`
  - `seed_2026_state_dict.pt`: `852e264af18f299ab1e17f72fdc22dee3601f95d50dbdf86ba38d1cb6947767d`
  - `seed_3405_state_dict.pt`: `e4556b26924b2ca18b326481070abd95a56784ca323bb3d9510d42090290b8b3`

## 7 **모델 재생성 파이프라인 실행가이드**

원본 데이터셋 출처: https://business.yelp.com/data/resources/open-dataset/

다운로드 받은 데이터를 아래 디렉토리 구조대로 생성

```python
data/
└── raw/
    ├── yelp_academic_dataset_business.json
    ├── yelp_academic_dataset_review.json
    └── yelp_academic_dataset_user.json
```

- 머신러닝 파이프라인 실행:

```bash
python pipeline/v05_ml
```

#### 1. 데이터 전처리 산출물 (`preprocessing.py`)

이 단계에서는 원본 JSON 파일들로부터 필터링, 추출, 병합, 피처 엔지니어링을 거쳐 모델 학습을 위한 최종 데이터셋이 만들어집니다.

| **단계** | **산출물 파일명** | **저장 경로 (프로젝트 루트 기준)** | **설명** |
| --- | --- | --- | --- |
| **업체 필터링** | `restaurant_businesses.parquet` | `data/interim/` | 핵심 음식점(Restaurants) 카테고리 업체 데이터 |
|  | `additional_culinary_businesses_v02.parquet` | `data/interim/` | 추가 미식 방문형(카페, 디저트 등) 업체 데이터 |
| **리뷰 추출** | `restaurant_reviews.parquet` | `data/interim/` | 핵심 음식점의 전체 리뷰 데이터 |
|  | `additional_culinary_reviews_v02.parquet` | `data/interim/` | 추가 미식 방문형 업체의 전체 리뷰 데이터 |
| **코호트 생성** | `culinary_rolling_cohort_master_v*.parquet` | `data/interim/rolling/` | (설정 파일 경로 우선) 롤링 코호트 기준 유저, 라벨, 연도 매핑 마스터 데이터 |
| **데이터셋 결합** | `modeling_dataset_rolling_v05_ml.parquet` | `data/processed/` | **[최종 결과물]** 모델 학습에 즉시 투입할 수 있는 43개+ 피처 및 타겟 결합 데이터 |

#### 2. 모델링 및 평가 산출물 (`modeling.py`)

전처리된 데이터셋을 기반으로 XGBoost 모델을 학습하고 하이퍼파라미터를 탐색한 뒤, 최종 평가 지표 및 리포트를 생성합니다.

| **분류** | **산출물 파일명** | **저장 경로 (프로젝트 루트 기준)** | **설명** |
| --- | --- | --- | --- |
| **최종 모델** | `xgboost_final_core_multiclass_v05.joblib` | `models/` | 학습이 완료된 최종 XGBoost 모델 객체 |
| **메타데이터** | `xgboost_multiclass_metadata_v05.json` | `models/` | 모델 구성, 평가 지표(F1, AUC 등), 선택 파라미터 등을 저장한 JSON 메타데이터 |
| **CRM 프로필** | `xgboost_final_test_retention_profiles_v05_ml.parquet` | `data/processed/predictions/` | Test 데이터 유저별 예측 확률, 상태(유지/약화/중단) 및 마케팅 타겟팅 우선순위(Rank/Score) 데이터 |
| **마크다운 리포트** | `xgboost_multiclass_model_performance_v05.md` | `reports/modeling/` | 깃허브나 문서에 바로 활용 가능한 모델 성능 및 Top 20% 정책 요약 마크다운 리포트 |
| **분석 결과 표** | `xgboost_multiclass_model_candidates_v05.csv` | `reports/tables/` | Grid Search로 탐색한 모든 하이퍼파라미터 및 임계값 조합별 성능 기록 |
|  | `xgboost_multiclass_validation_results_v05.csv` | `reports/tables/` | Fold별 교차 검증(CV) 및 Test 데이터의 Base 평가 지표 결과 |
|  | `xgboost_multiclass_confusion_matrix_v05.csv` | `reports/tables/` | OOF 및 Test 데이터에 대한 혼동 행렬(Confusion Matrix) 상세 수치 |
|  | `xgboost_multiclass_top_k_performance_v05.csv` | `reports/tables/` | 상위 5% ~ 40% 타겟팅 비율(Top-K)에 따른 Precision, Recall, Lift 지표 산출 기록 |
|  | `xgboost_feature_importance_v05.csv` | `reports/tables/` | Permutation Importance 기법을 통해 산출된 피처별 중요도 및 순위 데이터 |
- 딥러닝 파이프라인 실행:

```bash
python pipeline/v05_05_dl/preprocessing.py

python pipeline/v05_05_dl/build_features.py --user-json data/raw/yelp_academic_dataset_user.json --overwrite
python pipeline/v05_05_dl/train.py --overwrite

python pipeline/v05_05_dl/build_test_features.py --user-json data/raw/yelp_academic_dataset_user.json --overwrite
python pipeline/v05_05_dl/evaluate_test.py --overwrite
```

### 1단계: 학습/검증 피처 생성 (`build_features.py`)

이 단계에서는 2010년~2017년(Development) 데이터에 대한 시계열 시퀀스와 라이프사이클 피처를 생성합니다.

| **분류** | **산출물 파일명** | **저장 경로** | **설명** |
| --- | --- | --- | --- |
| **피처 데이터** | `lifecycle_features_v05_05.parquet` | `data/processed/experiments/` | 모델 학습용 유저 라이프사이클(Elite 이력, 가입 기간 등) 피처 |
|  | `monthly_core4_sequence_v05_05.parquet` | `data/processed/experiments/` | 모델 학습용 24개월 활동 시계열 시퀀스 피처 |
| **메타데이터** | `feature_build_metadata.json` | `reports/experiments/v05_05_dl/` | 피처 생성 과정의 행 개수, 컬럼 정보 및 해시값 기록 |

### 2단계: 모델 학습 및 OOF 평가 (`train.py`)

생성된 피처를 바탕으로 PyTorch 딥러닝 모델(Lifecycle Fusion H2)을 학습하고, 교차 검증(OOF)을 통해 최적의 임계값(Threshold)을 탐색합니다.

| **분류** | **산출물 파일명** | **저장 경로** | **설명** |
| --- | --- | --- | --- |
| **저장 모델** | `preprocessing.joblib` | `models/experiments/v05_05_dl/` | 시퀀스 및 라이프사이클 스케일러(StandardScaler) 전처리 객체 |
|  | `seed_{seed}_state_dict.pt` | `models/experiments/v05_05_dl/` | 시드(seed)별로 학습된 PyTorch 모델 가중치(Weights) 파일들 |
| **정보/리포트** | `metadata.json` | `models/experiments/v05_05_dl/` | 최종 모델의 아키텍처, 검증 점수 등 전체 메타데이터 |
|  | `performance.md` | `reports/experiments/v05_05_dl/` | OOF 검증 결과 및 성능 비교 요약 마크다운 리포트 |
| **평가 결과** | `selected_oof_candidate.json` | `reports/experiments/v05_05_dl/` | Grid Search로 선택된 최적의 타겟팅 임계값 및 결과 |
|  | `oof_predictions.parquet` | `reports/experiments/v05_05_dl/` | 검증 데이터(OOF)에 대한 시드별 및 앙상블 예측 확률 결과 |
|  | `threshold_candidates.csv` | `reports/experiments/v05_05_dl/` | 모든 임계값 조합에 대한 F1, AUC 성능 탐색 결과표 |
|  | `oof_confusion.csv` | `reports/experiments/v05_05_dl/` | OOF 예측에 대한 혼동 행렬(Confusion Matrix) |
|  | `oof_top_k_by_year.csv` | `reports/experiments/v05_05_dl/` | 연도별 Top-K 타겟팅 정밀도(Precision), Lift 등 상세 지표 |
|  | `oof_top_k_summary.csv` | `reports/experiments/v05_05_dl/` | Top-K 타겟팅 성능 요약 표 |
|  | `oof_model_comparison.csv` | `reports/experiments/v05_05_dl/` | 이전 기준 모델(v05_04 등)과의 OOF 성능 수치 비교 표 |
|  | `paired_bootstrap.csv` | `reports/experiments/v05_05_dl/` | 이전 모델과의 성능 차이에 대한 신뢰구간(Bootstrap) 기록 |

### 3단계: 테스트 피처 생성 (`build_test_features.py`)

학습 시 전혀 사용되지 않은 2018년(Test) 코호트 유저들을 대상으로만 피처를 생성합니다.

| **분류** | **산출물 파일명** | **저장 경로** | **설명** |
| --- | --- | --- | --- |
| **피처 데이터** | `test_lifecycle_features_v05_05.parquet` | `data/processed/experiments/` | 최종 테스트용 유저 라이프사이클 피처 |
|  | `test_monthly_core4_sequence_v05_05.parquet` | `data/processed/experiments/` | 최종 테스트용 24개월 활동 시계열 시퀀스 피처 |
| **메타데이터** | `test_feature_build_metadata.json` | `reports/experiments/v05_05_dl/` | 테스트 피처 생성 설정 및 데이터 무결성(검증) 메타데이터 |

### 4단계: 최종 테스트 셋 평가 (`evaluate_test.py`)

미리 고정된 딥러닝 모델 가중치와 최적화된 임계값을 Test 피처에 적용하여 2019년 결과를 예측하고, CRM용 프로필을 뽑아냅니다.

| **분류** | **산출물 파일명** | **저장 경로** | **설명** |
| --- | --- | --- | --- |
| **최종 결과** | `test_retention_profiles_v05_05_dl.parquet` | `data/processed/predictions/` | **[최종 산출물]** 마케팅팀 전달용 유저별 예측 상태 및 우선순위(Rank) 프로필 |
| **예측/결과** | `test_predictions.parquet` | `reports/experiments/v05_05_dl/` | 전체 Test 데이터에 대한 예측 확률 및 분류 상태 상세 기록 |
|  | `test_metrics.csv` | `reports/experiments/v05_05_dl/` | 최종 Test 셋 평가 지표 (F1, PR-AUC, Accuracy 등) 기록표 |
|  | `test_confusion.csv` | `reports/experiments/v05_05_dl/` | 최종 Test 예측 결과 혼동 행렬 |
|  | `test_top_k.csv` | `reports/experiments/v05_05_dl/` | Test 셋 대상의 Top-K (상위 마케팅 개입 대상) 성능 타겟팅 지표 |
| **정보/리포트** | `test_metrics.json` | `reports/experiments/v05_05_dl/` | 평가 지표 종합 및 OOF와의 성능 차이 등을 기록한 JSON |
|  | `test_performance.md` | `reports/experiments/v05_05_dl/` | 문서나 리드미에 바로 사용할 수 있는 딥러닝 테스트 결과 마크다운 리포트 |
