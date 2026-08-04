# 인공지능 데이터 전처리 결과서 (Data Preprocessing Report)

**프로젝트명**: Yelp 파워 리뷰어 리텐션 상태 예측 (가입 고객 이탈 예측)  
**기타 정보**: [SKN34-2nd-5Team GitHub Repository](https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN34-2nd-5Team)  
**기반 문서**: DEC-010 (v04 Cohort Time Structure) 및 v05 실험 파이프라인  
**작성일시**: 2026-08-04  

---

## 1. 개요 및 비즈니스/시간 구조 정의

### 1.1 프로젝트 목표 및 예측 타겟
Yelp 파워 리뷰어(Elite 유저)의 활동 저하 및 이탈을 사전에 방지하기 위해, 리뷰어의 향후 활동 상태를 아래 **3가지 클래스(3-Class Retention State)**로 예측합니다.
- **`retained`**: 활동 유지 (정상 활동)
- **`weakened`**: 활동 약화 (리뷰 작성 수 및 활성도 유의미 감소)
- **`stopped`**: 활동 중단 (완전 이탈)

### 1.2 코호트 및 시간 구조
- **개발 코호트 범위**: 2010–2017년 파워 리뷰어 선정 코호트 (총 31,420건)
- **OOF 검증 표본**: 2013–2017년 Expanding-Time 5-Fold CV (동일 OOF 비교 표본 24,596건)
- **관찰 기간 (Observation Window)**: 타겟 예측 시점 이전 **24개월 (M1 ~ M24)** 간의 월별 활동 이력
- **비교 기간**: 과거 12개월(Baseline Period) vs 최근 12개월(Recent Period) 행적 비교

### 1.3 비즈니스 타겟팅 및 비용/효익 가정
- **CRM 타겟팅**: 위험 점수(Risk Score) 상위 1,000명 / High Risk Tier 집중 리텐션 개입
- **비용/손실 구조**:
  - `stopped`(중단) 1건 발생 시 생애 가치(LTV) 및 리뷰 공급 손실 $L$
  - 리텐션 인센티브 및 케어 캠페인 비용 $C$
  - **목표**: 위험군 상위 1,000명 대상 **Precision@1000** 및 `retained` <-> `stopped` 간 **중증 오분류(Severe Misclassification)** 최소화

---

## 2. 데이터 누수(Data Leakage) 방지 및 분할 전략

### 2.1 데이터 누수 방지 원칙
- 24개월 관찰 기간(M1~M24) 이후의 미래 활동 데이터 완전히 격리 및 제거.
- 정답 라벨(`retention_state`) 산출 시점 이후 수집되는 모든 후속 변수 삭제.

### 2.2 검증 데이터 분할 전략 (Expanding-Time 5-Fold)
- 단순 랜덤 Split 시 동일 리뷰어의 시계열 정보 유출(Data Contamination)을 방지하기 위해 **선정연도 기준 Expanding-Time 5-Fold CV** 적용.
- 2013년부터 2017년까지 연도별 시계열 확장을 통해 실제 서비스 배포 환경과 동일한 타임 스플릿 검증.

---

## 3. 데이터 전처리 명세: v05_2 XGBoost (ML 정적/집계 피처)

머신러닝 모델(XGBoost)을 위해 24개월 시계열 데이터를 정적 통계량 및 트렌드 피처로 집계하여 전처리를 수행했습니다.

### 3.1 ML 피처 엔지니어링 단계 (Core43 → 45개 최종 피처)
1. **기본 피처 세트**: Core 43개 정적 피처
2. **1단계 피처 추가 (+9개)**:
   - `active_years`: 파워리뷰어 선정 연도 기준 활동 연차
   - `years_since_last_elite`: 엘리트 등급 선정 후 경과 기간
   - `review_count_slope_6m`: 최근 6개월 리뷰 감소 추세 (기울기)
   - `review_recent3m_vs_prev3m`: 직전 대비 최근 활동 급감 비율
   - `inactive_month_count_6m` / `3m`: 최근 6개월/3개월 비활동 월 수
   - `recency_vs_mean_interval`: 평소 작성 주기 대비 지연 일수
   - `unique_business_slope_6m`: 탐방 음식점 감소 추세
   - `months_since_last_new_business`: 신규 장소 탐색 중단 기간
3. **중요도 기반 피처 제외 (-8개)**:
   - `recent_interval_available`, `recent_revisit_rate`, `recent_new_vs_baseline_rate`, `active_month_diff`, `active_month_ratio`, `reviews_per_active_month_ratio`, `review_count_ratio` 등 중요도 0 이하 피처 제거
4. **부활 피처 (+1개)**:
   - `review_count_decline_rate`: 3개 타겟 클래스(`retained`/`weakened`/`stopped`) 간 평균값 차이가 뚜렷하여 부활 적용
5. **최종 ML 피처 데이터셋**: **45개 피처** (`modeling_dataset_rolling_v05_ml.parquet`)

### 3.2 2단계 경량화(v05_3) 피처 실험 결과
- 타겟 클래스 간 차이가 미미한 21개 피처를 추가 제외한 경량화 실험(v05_3) 진행 결과, OOF Macro F1이 0.5660에서 0.5623으로 하락하여 **45개 피처를 가진 v05_2 피처 세트를 최종 채택**함.

---

## 4. 데이터 전처리 명세: v05_05_dl (DL 시계열/라이프사이클 피처)

딥러닝 모델(`v05_05_dl Lifecycle Fusion H2`)을 위해 데이터셋을 **시계열 Branch**와 **라이프사이클 Branch** 2개 입력 신호로 분리 및 정규화 전처리를 수행했습니다.

### 4.1 시계열 Branch 전처리 (24개월 연속 시퀀스)
- **입력 형태**: `(Batch_Size, 24_Months, 4_Features)`
- **월별 Core 4개 입력 신호**:
  1. `monthly_review_count`: 월별 작성 리뷰 수
  2. `monthly_active_flag`: 월별 활동 여부 (0 또는 1)
  3. `monthly_unique_business_count`: 월별 방문한 서로 다른 업체 수
  4. `monthly_mean_interval_days`: 월별 평균 리뷰 작성 간격 (일)

### 4.2 라이프사이클 Branch 전처리 (정적 5개 피처)
- **입력 형태**: `(Batch_Size, 5_Features)`
- **라이프사이클 5개 정적 신호**:
  1. `account_age_days`: 계정 생성 후 경과일
  2. `past_elite_years`: 과거 Elite 선정 연도 총수
  3. `is_current_elite`: 선정연도 Elite 보유 여부 (0/1)
  4. `years_since_last_elite`: 마지막 Elite 선정 이후 경과 연도
  5. `consecutive_elite_years`: 최근 Elite 연속 유지 기간

### 4.3 정규화 및 수치 스케일링
- 시계열 및 라이프사이클 수치형 입력값에 대해 Train Set 기준 **StandardScaler(Z-score)** 정규화 적용.
- 연속적인 시계열 입력값의 결측 구간은 `0` 패딩 및 0/1 Masking으로 처리.

---

## 5. 전처리 요약 비교

| 구분 | v05_2 XGBoost (ML) | v05_05_dl (DL - 최종 채택) |
| :--- | :--- | :--- |
| **데이터 구조** | 24개월 통계 집계 정적 테이블 | 24개월 시계열 시퀀스 + 라이프사이클 정적 결합 |
| **피처 수** | 45개 (Core43 + 파생 - 저중요도) | 시계열 (24, 4) + 정적 (5) = 총 2개 테일러드 Branch |
| **스케일링** | 미적용 (트리 분할 방식) | StandardScaler (Z-score 정규화) |
| **최종 파일명** | `modeling_dataset_rolling_v05_ml.parquet` | `modeling_dataset_rolling_v05_dl.parquet` |