# 인공지능 데이터 전처리 결과서 (Data Preprocessing Report)

**프로젝트명**: Yelp 파워 리뷰어 리텐션 상태 예측 (가입 고객 이탈 예측)  
**기타 정보**: [SKN34-2nd-5Team GitHub Repository](https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN34-2nd-5Team)  
**기반 문서**: DEC-010 (v04 Cohort Time Structure) 및 v05 실험 파이프라인  
**작성일시**: 2026-08-04  

---

## 1. 개요 및 비즈니스/시간 구조 정의

### 1.1 프로젝트 목표 및 예측 타겟
Yelp 파워 리뷰어(Elite 유저)의 활동 저하 및 이탈을 사전에 방지하기 위해, 리뷰어의 향후 활동 상태를 아래 **3가지 클래스(3-Class Retention State)**로 예측합니다.
| 코드 | 영문명 | 화면 표현 | 타깃 연도 (파워 리뷰어 선정 익년) 조건 | (2018년)최종 평가 코호트 건수 (6,533건 기준) | 비고 |
|---:|---|---|---|---:|---|
| 0 | **`retained`** | 파워 지위 유지 | 리뷰 10건 이상이고 활동 월 3개월 이상 | 2,584건 (39.55%) | 파워 지위 유지군 |
| 1 | **`weakened`** | 파워 지위 약화 | 리뷰 1건 이상이며 리뷰 10건 미만이거나 활동 월 3개월 미만 | 3,065건 (46.91%) | 지위 상실 (Status Loss) |
| 2 | **`stopped`** | 리뷰 활동 중단 | 리뷰 0건 | 884건 (13.53%) | CRM 주요 타깃 관리 대상 |
![3class_retention_distribution](assets\readme\3class_retention_distribution.png)

### 1.2 코호트 및 시간 구조
- **개발 코호트 범위**: 2010–2017년 파워 리뷰어 선정 코호트 (총 31,420건)
| 코드 | 영문명 | 화면 표현 | 타깃 연도 (파워 리뷰어 선정 익년) 조건 | (2010-2017년)파워 리뷰어 선정 코호트 건수 (31,420건 기준) | 비고 |
|---:|---|---|---|---:|---|
| 0 | **`retained`** | 파워 지위 유지 | 리뷰 10건 이상이고 활동 월 3개월 이상 | 12,663건 (40.30%) | 파워 지위 유지군 |
| 1 | **`weakened`** | 파워 지위 약화 | 리뷰 1건 이상이며 리뷰 10건 미만이거나 활동 월 3개월 미만 | 13,882건 (44.18%) | 지위 상실 (Status Loss) |
| 2 | **`stopped`** | 리뷰 활동 중단 | 리뷰 0건 | 4875건 (15.51%) | CRM 주요 타깃 관리 대상 |

- **OOF 검증 표본**: 2013–2017년 Expanding-Time 5-Fold CV (동일 OOF 비교 표본 24,596건)
- **관찰 기간 (Observation Window)**: 타겟 예측 시점 이전 **24개월 (M1 ~ M24)** 간의 월별 활동 이력
- **비교 기간**: 과거 12개월(Baseline Period) vs 최근 12개월(Recent Period) 행적 비교
| **구분** | **코호트 선정 연도** | **표본 수 (건)** | **시간축 검증 역할 및 설명** |
| --- | --- | --- | --- |
| **전체 원본 데이터** | 2004–2022년 | 전체 이력 | User 2004년 시작, Review 2005–2022년 원본 데이터 |
| **개발 코호트 (Dev)** | 2010–2017년 | **31,420건** | 모델 학습 및 피처 엔지니어링 탐색용 전체 개발 세트 |
| **OOF 검증 표본 (CV)** | 2013–2017년 | **24,596건** | Expanding-Time 5-Fold × 3 seeds 공통 OOF 검증 표본 |
| **최종 평가 코호트 (Test)** | **2018년** | **6,533건** | **학습에 미포함된 2018년 선정 파워 리뷰어 코호트 (미래 일반화 성능 및 CRM 실무 배포 안정성 최종 검증)** |

### 1.3 비즈니스 타겟팅 및 비용/효익 가정
- **CRM 타겟팅**: 위험 점수(Risk Score) 상위 20% / 통합 검토 대상 우선 개입
- 위험 점수 계산: 최종 모델(`v05_05_dl`) 기준, `risk_score`는 보정된 이탈 확률이 아니라 위험 순위를 정하기 위한 모델 점수임
| 구분 | 조건 | 인원 | 지위 상실 Precision | Lift |
|---|---|---:|---:|---:|
| 통합 검토 대상 | 통합 우선순위 상위 20% | 1,307명 | 89.29% | 1.48× |
| 일반 모니터링 | 나머지 80% | 5,226명 | — | — |

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
| **항목** | **명세 및 설정값** | **비고** |
| --- | --- | --- |
| **타깃 변수명 (Target Variable)** | **`retention_state`** | 3-Class 다중 분류 (0: `retained`, 1: `weakened`, 2: `stopped`) |
| **전체 데이터 수 (Total Samples)** | **37,953건** | 개발 코호트(31,420건) + 최종 평가 코호트(6,533건) |
| **개발 코호트 수 (Dev Cohort)** | **31,420건** | 2010–2017년 파워 리뷰어 선정 코호트 전체 |
| **검증 데이터 수 (Validation / OOF)** | **24,596건** | 2013–2017년 Expanding-Time 5-Fold CV 공통 평가 표본 |
| **테스트 데이터 수 (Final Test)** | **6,533건** | 2018년 파워 리뷰어 선정 $\rightarrow$ 2019년 타깃 평가 코호트 |
| **관찰 기간 (Observation Window)** | **24개월 (M1 ~ M24)** | 타깃 예측 시점 직전 2년간의 월별 활동 행적 |
| **피처 수 (ML - v05_2 XGBoost)** | **45개 정적 집계 피처** | Core 43개 + 파생 9개 - 저중요도 8개 + 부활 1개 |
| **데이터 스케일링 (Normalization)** | **StandardScaler (Z-score)** | Train Set 기준 정규화 |
| **결측치 처리 (Imputation)** | **2단계 방어 체계** | 1) 도메인 지식 기반 사전 대체 (`-1`, `0.0`, `6.0` 등) 2) `SimpleImputer` 중앙값 대체 (`add_indicator=True`) |
| **최종 저장 파일명** | • **ML**: `modeling_dataset_rolling_v05_ml.parquet` | `data/processed/` 디렉터리 내 저장 |

### 4.1 ML 피처 엔지니어링 단계 (Core43 → 45개 최종 피처)

- **활동량 관련 지표 (Activity) - 11개**
1. `baseline_review_count`: 과거(Baseline) 총 작성 리뷰 수  
2. `baseline_active_months`: 과거 활성 월 수  
3. `baseline_reviews_per_active_month`: 과거 활성 월당 평균 작성 리뷰 수  
4. `recent_review_count`: 최근(Recent) 총 작성 리뷰 수  
5. `recent_active_months`: 최근 활성 월 수  
6. `recent_reviews_per_active_month`: 최근 활성 월당 평균 작성 리뷰 수  
7. `review_count_diff`: 리뷰 수 증감량 (`recent` - `baseline`)  
8. `review_count_decline_rate`: 리뷰 수 감소율  
9. **`active_month_decline_rate`**: 활성 달 수 감소율
10. `reviews_per_active_month_diff`: 월평균 리뷰 수 증감량  
11. `reviews_per_active_month_decline_rate`: 월평균 리뷰 수 감소율  
****
- **간격 및 최근성 관련 지표 (Interval & Recency) - 12개**
1. `baseline_mean_interval_days`: 과거 리뷰 작성 간격 평균(일)  
2. `baseline_median_interval_days`: 과거 리뷰 작성 간격 중앙값(일)  
3. `baseline_max_interval_days`: 과거 리뷰 작성 최대 간격(일)  
4. `baseline_recency_days`: 과거 기말 기준 경과일(Recency)  
5. `recent_mean_interval_days`: 최근 리뷰 작성 간격 평균(일)  
6. `recent_median_interval_days`: 최근 리뷰 작성 간격 중앙값(일)  
7. `recent_max_interval_days`: 최근 리뷰 작성 최대 간격(일)  
8. `recent_recency_days`: 최근 기말(예측 시점) 기준 경과일(Recency)  
9. `mean_interval_increase_days`: 평균 간격 증가량 (`recent` - `baseline`)  
10. `median_interval_increase_days`: 중앙값 간격 증가량  
11. `max_interval_increase_days`: 최대 간격 증가량  
12. `recency_increase_days`: 공백기(Recency) 증가량  
****
- **식당 탐색 및 다양성 관련 지표 (Business Diversity & Exploration) - 13개**
1. `baseline_unique_business_count`: 과거 방문 식당 다양성 수  
2. `recent_unique_business_count`: 최근 방문 식당 다양성 수  
3. `recent_revisited_business_count`: 최근 중복/재방문 식당 수  
4. `recent_new_vs_baseline_count`: 과거 대비 최근 신규 방문 식당 수  
5. `unique_business_count_diff`: 방문 식당 수 증감량  
6. `unique_business_ratio`: 방문 식당 수 비율  
7. `unique_business_decline_rate`: 방문 식당 수 감소율  
8. `baseline_new_business_count`: 과거 신규 등록 식당 리뷰 수  
9. `recent_new_business_count`: 최근 신규 등록 식당 리뷰 수  
10. `baseline_new_business_rate`: 과거 전체 대비 신규 식당 리뷰 비율  
11. `recent_new_business_rate`: 최근 전체 대비 신규 식당 리뷰 비율  
12. `new_business_count_diff`: 신규 식당 리뷰 수 증감량  
13. `new_business_rate_decline`: 신규 식당 리뷰 비율 감소 폭  
****
- **추가/파생 피처 (Added Features) - 9개**  
1. `active_years`: 파워 리뷰어 선정 연도 기준 활동 연차  
2. `years_since_last_elite`: 엘리트 등급 선정 후 경과 기간  
3. `review_count_slope_6m`: 최근 6개월 리뷰 감소 추세 (기울기)  
4. `review_recent3m_vs_prev3m`: 직전 3개월 대비 최근 3개월 활동 급감 비율  
5. `inactive_month_count_6m`: 최근 6개월 비활동 월 수  
6. `inactive_month_count_3m`: 최근 3개월 비활동 월 수  
7. `recency_vs_mean_interval`: 평소 작성 주기 대비 지연 일수  
8. `unique_business_slope_6m`: 탐방 음식점 감소 추세  
9. `months_since_last_new_business`: 신규 장소 탐색 중단 기간

**최종 ML 피처 데이터셋**: **45개 피처** (`modeling_dataset_rolling_v05_ml.parquet`)

### 4.2 결측치 처리
- 비율 피처(예: review_count_ratio, unique_business_ratio 등) 산출 시 분모가 0이 되어 연산 오류가 발생하는 것을 방지하기 위해 분모 0을 NaN으로 치환
- 활동 이력이 없거나 특정 이벤트 경험이 없는 유저의 결측치에 대해 비즈니스 의미에 부합하도록 값을 -1 혹은 0으로 사전 보정을 수행
- 머신러닝 학습 파이프라인 내에 SimpleImputer(strategy='median', add_indicator=True)를 추가하여, Train Set 기준의 중앙값으로 자동 대체함과 동시에 add_indicator=True 옵션을 통해 결측 발생 유무 자체를 추가 피처 신호로 모델이 학습할 수 있도록 구현

### 4.3 정규화 및 수치 스케일링
- 수치형 입력값에 대해 Train Set 기준 **StandardScaler(Z-score)** 정규화 적용.

---

## 5. 데이터 전처리 명세: v05_05_dl (DL 시계열/라이프사이클 피처)

딥러닝 모델(`v05_05_dl Lifecycle Fusion H2`)을 위해 데이터셋을 **시계열 Branch**와 **라이프사이클 Branch** 2개 입력 신호로 분리 및 정규화 전처리를 수행했습니다.
| **항목** | **명세 및 설정값** | **비고** |
| --- | --- | --- |
| **최종 선정 모델** | **`v05_05_dl` Lifecycle Fusion H2** | GRU 시계열 Branch와 Lifecycle MLP Branch를 결합한 계층형 분류 모델 |
| **타깃 변수명** | **`retention_state`** | 3-Class 분류: 0 `retained`, 1 `weakened`, 2 `stopped` |
| **전체 데이터 수** | **37,953건** | 개발 코호트 31,420건 + 최종 테스트 6,533건 |
| **개발 코호트 수** | **31,420건** | 2010–2017년 파워 리뷰어 선정 코호트 |
| **OOF 검증 데이터 수** | **24,596건** | 2013–2017년 Expanding-Time 5-Fold 공통 평가 표본 |
| **최종 테스트 데이터 수** | **6,533건** | 2018년 선정 코호트의 2019년 활동 상태 평가 |
| **관찰 기간** | **24개월(M1~M24)** | 타깃 평가 직전 2년간의 월별 리뷰 활동 |
| **시계열 입력 형태** | **`(Batch, 24, 4)`** | 24개월 × 월별 활동 채널 4개 |
| **정적 입력 형태** | **`(Batch, 5)`** | 시점 안전하게 생성한 Lifecycle 피처 5개 |
| **시계열 개발 데이터 행 수** | **754,080행** | 31,420명 × 24개월 |
| **시계열 테스트 데이터 행 수** | **156,792행** | 6,533명 × 24개월 |
| **스케일링** | **선택적 `log1p` + StandardScaler** | 각 학습 Fold 내부에서만 적합 |
| **개발 피처 파일** | `monthly_core4_sequence_v05_05.parquet` | 24개월 Core4 시퀀스 |
|  | `lifecycle_features_v05_05.parquet` | Lifecycle 정적 피처 |
| **테스트 피처 파일** | `test_monthly_core4_sequence_v05_05.parquet` | 2018년 시점 테스트 시퀀스 |
|  | `test_lifecycle_features_v05_05.parquet` | 2018년 시점 Lifecycle 피처 |

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