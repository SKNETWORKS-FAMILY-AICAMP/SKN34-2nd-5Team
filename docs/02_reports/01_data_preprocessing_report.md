# 인공지능 데이터 전처리 결과서 (Data Preprocessing Report)

**프로젝트명**: Yelp 파워 리뷰어 리텐션 상태 예측 (가입 고객 이탈 예측)  
**기타 정보**: [SKN34-2nd-5Team GitHub Repository](https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN34-2nd-5Team)  
**기반 문서**: DEC-010 (v04 Cohort Time Structure) 및 v05 실험 파이프라인  
**작성일시**: 2026-08-04  

---

## 1. 개요 및 비즈니스/시간 구조 정의

### 1.1 프로젝트 목표 및 예측 타겟
Yelp 파워 리뷰어(Elite 유저)의 활동 저하 및 이탈을 사전에 방지하기 위해, 리뷰어의 향후 활동 상태를 아래 **3가지 클래스(3-Class Retention State)**로 예측합니다.
| 코드 | 영문명 | 화면 표현 | 타깃 연도 (파워 리뷰어 선정 익년) 조건 |
|---:|---|---|---|
| 0 | **`retained`** | 파워 지위 유지 | 리뷰 10건 이상이고 활동 월 3개월 이상 |
| 1 | **`weakened`** | 파워 지위 약화 | 리뷰 1건 이상이며 리뷰 10건 미만이거나 활동 월 3개월 미만 |
| 2 | **`stopped`** | 리뷰 활동 중단 | 리뷰 0건 |

### 1.2 코호트 및 시간 구조
- **개발 코호트 범위**: 2010–2017년 파워 리뷰어 선정 코호트 (총 31,420건)
- **OOF 검증 표본**: 2013–2017년 Expanding-Time 5-Fold CV (동일 OOF 비교 표본 24,596건)
- **관찰 기간 (Observation Window)**: 타겟 예측 시점 이전 **24개월 (M1 ~ M24)** 간의 월별 활동 이력
- **비교 기간**: 과거 12개월(Baseline Period) vs 최근 12개월(Recent Period) 행적 비교

### 1.3 비즈니스 타겟팅 및 비용/효익 가정 [수정 필요]
- **CRM 타겟팅**: 위험 점수(Risk Score) 상위 20% / 통합 검토 대상 우선 개입
- 위험 점수 계산: 
| 구분 | 조건 | 인원 | 지위 상실 Precision | Lift |
|---|---|---:|---:|---:|
| 통합 검토 대상 | 통합 우선순위 상위 20% | 832명 | 92.91% | 1.48× |
| 일반 모니터링 | 나머지 80% | 3,325명 | — | — |

---

## 2. 원본 데이터셋 명세 (Raw Dataset Overview)

프로젝트에 사용된 원본 데이터셋은 Yelp Open Dataset으로, 플랫폼 내 비즈니스, 유저, 리뷰 간의 상호작용 데이터를 포함하고 있습니다.

- 원본 데이터셋 출처: https://business.yelp.com/data/resources/open-dataset/
- 데이터 포맷: JSON (Line-delimited JSON)

### 2.1 주요 파일 목록 및 명세
| 파일명 | 설명 | 주요 컬럼 / 필드 | 비고 |
| --- | --- | --- | --- |
| **`yelp_academic_dataset_business.json`** | Yelp 플랫폼 내 전체 업체 메타데이터 | `business_id`, `name`, `address`, `city`, `state`, `postal_code`, `latitude`, `longitude`, `stars`, `review_count`, `is_open`, `categories` | 위치 및 카테고리 기반 1차/2차 타깃 필터링 대상 |
| **`yelp_academic_dataset_review.json`** | 유저가 작성한 원본 리뷰 데이터 (약 5GB) | `review_id`, `user_id`, `business_id`, `stars`, `useful`, `funny`, `cool`, `date` | Chunksize 연산 및 DuckDB 활용 메모리 최적화 추출 |
| **`yelp_academic_dataset_user.json`** | 플랫폼 가입 유저의 프로필 및 엘리트 이력 데이터 | `user_id`, `name`, `review_count`, `yelping_since`, `elite`, `friends`, `fans`, `average_stars` | 충성도, 활동 연차 및 엘리트 등급 변수 추출 대상 |

---

## 3. 데이터 누수(Data Leakage) 방지 및 분할 전략

### 3.1 데이터 누수 방지 원칙
- 24개월 관찰 기간(M1~M24) 이후의 미래 활동 데이터 완전히 격리 및 제거.
- 정답 라벨(`retention_state`) 산출 시점 이후 수집되는 모든 후속 변수(useful, fans 등) 삭제.

### 3.2 검증 데이터 분할 전략 (Expanding-Time 5-Fold)
- 단순 랜덤 Split 시 동일 리뷰어의 시계열 정보 유출(Data Contamination)을 방지하기 위해 **선정연도 기준 Expanding-Time 5-Fold CV** 적용.
- 2013년부터 2017년까지 연도별 시계열 확장을 통해 실제 서비스 배포 환경과 동일한 타임 스플릿 검증.

---

## 4. 데이터 전처리 명세: v05_2 XGBoost (ML 정적/집계 피처)

머신러닝 모델(XGBoost)을 위해 24개월 시계열 데이터를 정적 통계량 및 트렌드 피처로 집계하여 전처리를 수행했습니다.

### 4.1 ML 피처 엔지니어링 단계 (Core43 → 45개 최종 피처)
1. **기본 피처 세트**: Core 43개 정적 피처
  #### 활동량 기본 지표 (Activity Volume)

  유저가 '얼마나 많이, 자주' 리뷰를 썼는지 과거와 최근을 비교합니다.

  - **`baseline_review_count`**: 과거(Baseline) 기간 동안 작성한 총 리뷰 수입니다.
  - **`baseline_active_months`**: 과거 기간 동안 1개 이상 리뷰를 작성한 '활성 달(Month) '의 수입니다.
  - **`baseline_reviews_per_active_month`**: 과거 활성 달 1개월당 평균적으로 작성한   리뷰 수입니다. (리뷰 작성의 밀도)
  - **`recent_review_count`**: 최근(Recent) 기간 동안 작성한 총 리뷰 수입니다.
  - **`recent_active_months`**: 최근 기간 동안 리뷰를 작성한 활성 달의 수입니다.
  - **`recent_reviews_per_active_month`**: 최근 활성 달 1개월당 평균 작성 리뷰 수입니다.

  #### 활동량 변화 및 감소율 (Activity Changes)

  과거 대비 최근에 활동이 얼마나 줄었는지(혹은 늘었는지)를 다각도로 측정합니다. 이탈(중단)  을 예측하는 가장 직접적인 신호입니다.

  - **`review_count_diff`**: 리뷰 수 증감량 (`recent` - `baseline`). 음수면 리뷰가  줄어든 것입니다.
  - **`review_count_ratio`**: 리뷰 수 비율 (`recent` / `baseline`). 1보다 작으면  활동이 감소한 것입니다.
  - **`review_count_decline_rate`**: 리뷰 수 감소율. (비율을 % 감소폭으로 변환한 지표로   추정됨).
  - **`active_month_diff`**: 활성 달 수 증감량 (`recent` - `baseline`).
  - **`active_month_ratio`**: 활성 달 수 비율 (`recent` / `baseline`).
  - **`active_month_decline_rate`**: 활성 달 수 감소율.
  - **`reviews_per_active_month_diff`**: 월평균 리뷰 수 증감량. (달마다 쓰던 양 자체가  줄었는지 파악).
  - **`reviews_per_active_month_ratio`**: 월평균 리뷰 수 비율.
  - **`reviews_per_active_month_decline_rate`**: 월평균 리뷰 수 감소율.

  #### 간격 및 최근성 지표 (Interval & Recency)

  리뷰와 리뷰 사이의 시간 간격(Interval)과, 마지막 리뷰로부터 지난 시간(Recency)을  측정합니다. 열정이 식어가는 패턴을 잡습니다.

  - **`baseline_mean_interval_days`**: 과거 기간 중 리뷰 작성 간격의 평균(일수)입니다.
  - **`baseline_median_interval_days`**: 과거 기간 중 리뷰 작성 간격의 중앙값(일수) 입니다. (이상치 영향을 덜 받음).
  - **`baseline_max_interval_days`**: 과거 기간 중 가장 길었던 리뷰 작성 간격입니다.
  - **`baseline_recency_days`**: 과거 기간의 마지막 시점 기준으로, 가장 마지막 리뷰를 쓴  지 며칠이 지났는지입니다.
  - **`recent_mean_interval_days`**: 최근 기간 중 리뷰 작성 간격의 평균(일수)입니다.
  - **`recent_median_interval_days`**: 최근 기간 중 리뷰 작성 간격의 중앙값(일수)입니다.
  - **`recent_max_interval_days`**: 최근 기간 중 가장 길었던 리뷰 작성 간격입니다.
  - **`recent_recency_days`**: 최근 기간의 마지막 시점(예측 시점) 기준으로, 마지막  리뷰를 쓴 지 며칠이 지났는지입니다.
  - **`recent_interval_available`**: 최근 기간에 작성 간격을 계산할 수 있을 만큼(2개  이상) 리뷰를 썼는지 여부(Boolean/Indicator)입니다.

  #### 간격 변화량 (Interval Increases)

  작성 주기가 과거보다 얼마나 늘어지고 있는지를 보여줍니다.

  - **`mean_interval_increase_days`**: 평균 간격 증가량 (`recent` - `baseline`). 이 값이 크면 뜸해지고 있다는 뜻입니다.
  - **`median_interval_increase_days`**: 중앙값 간격 증가량.
  - **`max_interval_increase_days`**: 최대 간격 증가량.
  - **`recency_increase_days`**: 최근성(공백기) 증가량. (마지막 리뷰 이후로 잠수 탄   기간이 과거보다 길어졌는지 파악).

  ### 5. 비즈니스(식당) 다양성 및 탐색 지표 (Business Diversity & Exploration)

  유저가 똑같은 식당만 가는지, 아니면 새로운 식당을 계속 발굴(탐색)하는지를 통해 플랫폼에   대한 흥미도를 측정합니다.

  - **`baseline_unique_business_count`**: 과거 기간에 리뷰를 남긴 '서로 다른' 식당의  수입니다. (다양성)
  - **`recent_unique_business_count`**: 최근 기간에 리뷰를 남긴 서로 다른 식당의  수입니다.
  - **`recent_revisited_business_count`**: 최근 기간에 방문한 식당 중, 같은 기간 내에   '재방문(중복 리뷰)'한 식당의 수입니다.
  - **`recent_new_vs_baseline_count`**: 최근에 리뷰를 남긴 식당 중, *과거 기간에는 간   적이 없는(새로운)* 식당의 수입니다.
  - **`unique_business_count_diff`**: 서로 다른 식당 수 증감량 (`recent` -  `baseline`).
  - **`unique_business_ratio`**: 서로 다른 식당 수 비율.
  - **`unique_business_decline_rate`**: 서로 다른 식당 수 감소율.
  - **`recent_revisit_rate`**: 최근 리뷰 중 재방문(중복) 리뷰의 비율입니다. (이 값이  높으면 새로운 탐색을 멈췄다는 신호일 수 있음).
  - **`recent_new_vs_baseline_rate`**: 최근 리뷰 중 과거에 안 가본 '완전 새로운 식당'의   비율입니다.

  ### 6. 옐프(Yelp) 신규 등록 비즈니스 지표 (New Business Adoption)

  플랫폼에 갓 등록된 '새로운 식당'을 남들보다 먼저 리뷰하는 얼리 어답터 성향을 측정합니다.  파워 리뷰어의 핵심 동력 중 하나입니다.

  - **`baseline_new_business_count`**: 과거 기간에 리뷰한 식당 중, (플랫폼 자체에) 새로   등록된 지 얼마 안 된 식당의 수입니다.
  - **`recent_new_business_count`**: 최근 기간에 리뷰한 식당 중, 새로 등록된 식당의   수입니다.
  - **`baseline_new_business_rate`**: 과거 전체 리뷰 중 신규 등록 식당을 리뷰한   비율입니다.
  - **`recent_new_business_rate`**: 최근 전체 리뷰 중 신규 등록 식당을 리뷰한   비율입니다.
  - **`new_business_count_diff`**: 신규 등록 식당 리뷰 수 증감량.
  - **`new_business_rate_decline`**: 신규 등록 식당 리뷰 비율의 감소 폭(또는 감소율). 유저의 '발견의 재미(트렌드세터 성향)'가 식었는지를 나타냅니다.
  
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

### 4.2 2단계 경량화(v05_3) 피처 실험 결과
- 타겟 클래스 간 차이가 미미한 21개 피처를 추가 제외한 경량화 실험(v05_3) 진행 결과, OOF Macro F1이 0.5660에서 0.5623으로 하락하여 **45개 피처를 가진 v05_2 피처 세트를 최종 채택**함.

### 4.3 정규화 및 수치 스케일링
- 수치형 입력값에 대해 Train Set 기준 **StandardScaler(Z-score)** 정규화 적용.

---

## 5. 데이터 전처리 명세: v05_05_dl (DL 시계열/라이프사이클 피처)

딥러닝 모델(`v05_05_dl Lifecycle Fusion H2`)을 위해 데이터셋을 **시계열 Branch**와 **라이프사이클 Branch** 2개 입력 신호로 분리 및 정규화 전처리를 수행했습니다.

### 5.1 시계열 Branch 전처리 (24개월 연속 시퀀스)
- **입력 형태**: `(Batch_Size, 24_Months, 4_Features)`
- **월별 Core 4개 입력 신호**:
  1. `monthly_review_count`: 월별 작성 리뷰 수
  2. `monthly_active`: 월별 활동 여부 (0 또는 1)
  3. `monthly_unique_business_count`: 월별 방문한 서로 다른 업체 수
  4. `monthly_mean_interval_days`: 월별 평균 리뷰 작성 간격 (일)

### 5.2 라이프사이클 Branch 전처리 (정적 5개 피처)
- **입력 형태**: `(Batch_Size, 5_Features)`
- **라이프사이클 5개 정적 신호**:
  1. `account_age_days`: 계정 생성 후 경과일
  2. `elite_year_count_prior`: 과거 Elite 선정 연도 총수
  3. `is_elite_selection_year`: 선정연도 Elite 보유 여부 (0/1)
  4. `years_since_last_elite`: 마지막 Elite 선정 이후 경과 연도
  5. `recent_elite_streak`: 최근 Elite 연속 유지 기간

### 5.3 정규화 및 수치 스케일링
- 시계열 및 라이프사이클 수치형 입력값에 대해 Train Set 기준 **log1p + StandardScaler(Z-score)** 정규화 적용.

---

## 6. 전처리 요약 비교

| 구분 | v05_2 XGBoost (ML) | v05_05_dl (DL - 최종 채택) |
| :--- | :--- | :--- |
| **데이터 구조** | 24개월 통계 집계 정적 테이블 | 24개월 시계열 시퀀스 + 라이프사이클 정적 결합 |
| **피처 수** | 45개 (Core43 + 파생 - 저중요도) | 시계열 (24, 4) + 정적 (5) = 총 2개 테일러드 Branch |
| **스케일링** | 미적용 (트리 분할 방식) | StandardScaler (Z-score 정규화) |
| **최종 파일명** | `modeling_dataset_rolling_v05_ml.parquet` | `modeling_dataset_rolling_v05_dl.parquet` |