# 프로젝트 요구사항 정의서 (Project Requirements)

**프로젝트명**: Yelp 파워 리뷰어 리텐션 상태 예측  
**기타 정보**: [SKN34-2nd-5Team GitHub Repository](https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN34-2nd-5Team)  
**작성일시**: 2026-08-04  

---

## 1. 프로젝트 개요

본 프로젝트는 Yelp 파워 리뷰어의 24개월간 시계열 행동 및 라이프사이클 데이터를 기반으로 향후 12개월간의 활동 상태(`retained`, `weakened`, `stopped`)를 예측하고, 이를 CRM 시스템과 연동할 수 있는 추론 파이프라인 및 대시보드를 구축하는 프로젝트입니다.

---

## 2. 시스템 기능 요구사항 (Functional Requirements)

### FR-01: 시계열 코호트 데이터 전처리 파이프라인
- **FR-01.1**: 원본 Yelp 학술 데이터셋(Business, Review, User JSON)을 통합하여 2010–2017 코호트 기준 24개월 시계열 롤링 마스터 데이터셋을 생성해야 한다.
- **FR-01.2**: 관찰 기간(M1~M24) 이후의 미래 데이터 유출(Data Leakage)이 발생하지 않도록 컬럼 필터링 검증을 수행해야 한다.

### FR-02: ML 및 DL 이원화 피처 공급 파이프라인
- **FR-02.1 (ML)**: XGBoost 등 머신러닝 학습을 위해 Core43 + 파생피처 9개 - 저중요도 피처 8개 + 부활 피처 1개 = **총 45개 정적 집계 피처**를 파이프라인에서 자동 생성해야 한다.
- **FR-02.2 (DL)**: 딥러닝 학습을 위해 **24개월 시계열 시퀀스(월별 4개 신호)**와 **정적 라이프사이클(5개 신호)**을 분리 가공하여 모델 인풋으로 공급해야 한다.

### FR-03: 계층형 딥러닝 모델 학습 및 검증
- **FR-03.1**: 최종 채택 모델인 `v05_05_dl (Lifecycle Fusion H2)` 구조를 구현해야 한다.
  - 시계열 Branch: GRU (Hidden 64)
  - 라이프사이클 Branch: MLP (Hidden 16)
  - 계층형 Head (H2): 1단계(retained/at-risk) -> 2단계(weakened/stopped)
- **FR-03.2**: Expanding-Time 5-Fold Cross Validation을 수행하고 OOF Macro F1 및 Precision@1000 지표를 기록해야 한다.

### FR-04: 추론 및 CRM 타겟팅 프로필 생성
- **FR-04.1**: 학습된 모델 가중치(`models/v05_05_dl_lifecycle_fusion_h2.pt`)를 로드하여 신규 유저 데이터에 대한 3-Class 확률값 및 이탈 위험 점수(Risk Score)를 산출해야 한다.
- **FR-04.2**: 위험 점수 상위 1,000명 및 Risk Tier(High/Medium/Low)가 매핑된 **CRM 타겟팅 프로필 Parquet 파일**을 자동 출력해야 한다.

---

## 3. 비기능 및 기술 요구사항 (Non-Functional Requirements)

### NFR-01: 재현성 보장 (Reproducibility)
- 모든 난수 생성기(Numpy, PyTorch, Scikit-learn 등)의 시드를 `random_seed = 42`로 고정하여 어느 환경에서든 동일한 결과를 재현할 수 있어야 한다.

### NFR-02: 추론 성능 및 경량성
- 단일/배치 추론 시 1,000건 기준 **1초 이내**에 Risk Score 및 Tier 분류 결과를 반환해야 한다.

### NFR-03: 모듈화 및 확장성
- 파이프라인 코드는 `pipeline/` 디렉토리 내 `preprocessing.py`와 `modeling.py`로 모듈화되어 CLI 명령으로 단일 실행 가능해야 한다.

---

## 4. 최종 수락 기준 및 성능 지표 (Acceptance Criteria)

| 평가 항목 | 수락 기준 (KPI) | `v05_05_dl` 달성 성과 | 수락 여부 |
| :--- | :--- | :---: | :---: |
| **OOF Macro F1** | $\ge 0.5700$ | **0.5763** | **Pass** |
| **OOF Macro PR-AUC** | $\ge 0.5900$ | **0.5980** | **Pass** |
| **Precision@1000** | $\ge 90.0\%$ | **90.60%** | **Pass** |
| **중증 오분류 비율** | $\le 2.5\%$ | **2.19% (538건)** | **Pass** |
| **시드 고정 재현성** | 100% 동일 수치 재현 | **완전 재현 확인** | **Pass** |