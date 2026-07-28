# React 데이터 출처 (v04)

`app/`(React)가 v04 모델 산출물을 어떻게 읽고, 어떤 부분은 그대로 pass-through 하고
어떤 부분은 파이프라인 산출물에서 파생하는지 정의한다. Streamlit 쪽 데이터 계약은
[`STREAMLIT_DATA_CONTRACT.md`](STREAMLIT_DATA_CONTRACT.md) 참고 — 이 문서는 그 v04
산출물을 React가 어떻게 소비하는지 설명하는 짝문서다.

React는 자체 백엔드/API가 없다. `scripts/export_frontend_data.py`가 Streamlit의
`archive/app_streamlit_v04/core` 모듈을 그대로 불러와서, 화면별로 필요한 값을 JSON으로
내보내면(`app/src/data/*.json`, `app/public/data/reviewer-details.json`) React는 그걸
정적 파일로 읽기만 한다. 권역·월별 활동 계산은 export 스크립트가 원본 리뷰를 직접
읽지 않고 `pipeline/v04/derived_reviewer_activity.py`가 생성한 Parquet을 소비한다.

```powershell
.\.venv\Scripts\python.exe pipeline\v04\derived_reviewer_activity.py
.\.venv\Scripts\python.exe scripts\export_frontend_data.py
```

---

## 1. 데이터 소비 방식 두 가지

| 방식 | 의미 | 해당 화면 |
|---|---|---|
| **pass-through** | 모델 프로파일(`final_test_retention_profiles_v04.parquet`)이나 리포트 CSV의 컬럼을 그대로, 혹은 단순 포맷팅만 거쳐 JSON으로 옮김 | 운영 홈, 리뷰어 관리, 리뷰어 상세의 활동 변화/작성 주기/사후 검증 탭, 플레이북, Trust Center의 v04 기본 지표 |
| **파생(derived)** | 원천 리뷰에서 파이프라인이 만든 리뷰어 단위 Parquet 또는 별도 리포트 파일을 JSON으로 변환 | 콘텐츠 위험(권역 집계), 리뷰어 상세의 월별 타임라인, Trust Center의 v02/v03 이전 모델 비교 |

이 문서는 **파생** 쪽만 다룬다 — pass-through는 컬럼명만 다를 뿐 별도 로직이 없어서
문서화할 게 없다.

---

## 2. 콘텐츠 위험 — 권역별 집계

화면: `/regional` ([RegionalRiskPage.jsx](../app/src/pages/RegionalRiskPage.jsx))
파이프라인: [`derived_reviewer_activity.py`](../pipeline/v04/derived_reviewer_activity.py)
내보내기 함수: [`export_regional()`](../scripts/export_frontend_data.py)

### 2-1. 원천 데이터

| 파일 | 사용한 컬럼 | 용도 |
|---|---|---|
| `data/processed/reviewer_region_v04.parquet` | `sample_id`, `user_id`, `state`, `top_city` | 파이프라인이 확정한 리뷰어 단위 리뷰 활동 권역 |
| `final_test_retention_profiles_v04.parquet` (모델 프로파일) | `sample_id`, `predicted_state`, `crm_target`, `comparison_year`, `selection_year` | 이미 나온 모델 예측 결과를 지역 기준으로 재집계 |

`reviewer_region_v04.parquet`의 원천은
`restaurant_reviews.parquet`, `additional_culinary_reviews.parquet`,
`restaurant_businesses.parquet`이다. 상세 계약은
[`DERIVED_REVIEWER_DATA_CONTRACT_v04.md`](../database/docs/DERIVED_REVIEWER_DATA_CONTRACT_v04.md)를
따른다.

### 2-2. 처리 단계

1. 파이프라인이 두 리뷰 파일(`restaurant_reviews` + `additional_culinary_reviews`)을
   합쳐 하나의 리뷰 테이블을 만든다.
2. 모델의 관찰 구간(`comparison_year`~`selection_year`, 현재 v04 기준 2017~2018)에
   해당하는 리뷰만 남긴다.
3. `restaurant_businesses`와 조인해서 리뷰마다 `state`를 붙인다. `state`가 없는(조인
   실패) 리뷰는 버린다.
4. **리뷰어별로 그 구간에 가장 많이 리뷰를 남긴 `state`를 그 리뷰어의 "권역"으로
   확정한다.** 이건 거주지·직장이 아니라 순수하게 관찰된 리뷰 활동 기준이다 — city
   단위(208개)로 하면 교외가 도심에서 갈라져 나가서 의미가 흐려지므로 state로 묶는다.
5. 리뷰어별 선택 권역과 그 안의 최다 리뷰 도시를
   `reviewer_region_v04.parquet`에 저장한다.
6. export 스크립트 또는 DB View가 권역별로 묶어서 `predicted_state`를 집계한다 —
   유지(0)/약화(1)/중단(2) 인원수,
   고위험 비율(`highRiskRate` = (약화+중단) / 전체), CRM 대상 수(`crmTargets` =
   `crm_target` 합).
7. 표본이 30명(`minimum_reviewers`) 미만인 권역은 순위에서 제외하지 않고 `belowMinimum`
   플래그만 붙여 별도 표시한다 — 소수 표본의 비율이 왜곡돼 보이는 걸 막기 위함.

### 2-3. 커버리지 (2026-07-28 기준 확인값)

- 전체 6,533명 중 100% 권역 매핑 성공(`coveredReviewers` == `totalReviewers`).
- 14개 권역, 최소 표본 49명(DE) — 30명 기준에 걸려 숨겨지는 권역 없음.
- 1위 권역: PA(Philadelphia 중심) 1,433명.

### 2-4. 의도적으로 하지 않은 것

- **지역별 예측을 새로 하지 않는다.** `predicted_state`는 이미 v04 모델이 계산한 값을
  그대로 재집계할 뿐이다.
- 리뷰 공급 변화(review supply change) 지표는 한때 넣었다가 제거했다 — 코호트 자격
  조건(`recent_review_count`에만 최소 리뷰 수 하한이 있고 `baseline`에는 없음) 때문에
  전 권역에서 예외 없이 "증가"로만 나오는 구조적 아티팩트였다. 자세한 경위는
  [`REACT_V04_PARITY_PLAN.md`](ui/REACT_V04_PARITY_PLAN.md)의 "리뷰 공급 변화 지표
  제거" 절 참고.

---

## 3. 리뷰 수 이중 소스 — 두 화면에 공통되는 버그와 수정

권역과 월별 활동은
[`derived_reviewer_activity.py`](../pipeline/v04/derived_reviewer_activity.py)의
동일한 리뷰 결합 함수를 공유한다. export 스크립트는 원본 리뷰를 다시 읽지 않는다.

**발견 경위**: 월별 타임라인을 만들면서 `restaurant_reviews.parquet` 하나만으로 리뷰어별
월간 리뷰 수를 더해보니, 모델 프로파일의 `baseline_review_count` + `recent_review_count`
합계와 어긋나는 경우가 대부분이었다. 전체 6,533명 기준으로 검증한 결과:

- 정확히 일치: 36.9%
- 평균 부족분: 약 2건, 중앙값 1건, 최대 40건 부족
- 63.1%의 리뷰어가 실제보다 적게 집계됨

**원인**: `pipeline/v04/preprocessing.py`의 코호트 생성 SQL이
`restaurant_reviews.parquet`와 `additional_culinary_reviews.parquet` 두 파일을
`UNION ALL`로 합쳐서 리뷰 수를 계산한다. legacy
`additional_culinary_reviews_v02.parquet` 파일명도 입력 호환을 위해 지원한다.

**수정**: 파이프라인에서 두 파일을 합친 뒤 표본별 월간 리뷰 합계가 프로필의
`baseline_review_count + recent_review_count`와 전원 일치해야만 산출물을 저장한다.

---

## 4. 리뷰어 상세 — 월별 타임라인

화면: `/reviewers/:reviewerId`의 "월별 타임라인" 탭
([ReviewerDetailPage.jsx](../app/src/pages/ReviewerDetailPage.jsx),
[MonthlyActivityChart.jsx](../app/src/components/reviewer-detail/MonthlyActivityChart.jsx))
내보내기 함수: [`export_monthly_activity()`](../scripts/export_frontend_data.py) (`scripts/export_frontend_data.py:649`)

### 4-1. 원천 데이터

| 파일 | 사용한 컬럼 | 용도 |
|---|---|---|
| `data/processed/reviewer_monthly_activity_v04.parquet` | `sample_id`, `year_month`, `review_count`, `unique_business_count` | 파이프라인이 만든 표본별 월간 활동 |
| `final_test_retention_profiles_v04.parquet` (모델 프로파일) | `sample_id`, `user_id`, `comparison_year`, `selection_year` | 표본·사용자 매핑과 관찰 구간 검증 |

이 화면은 원래 Streamlit이 `data/processed/predictions/reviewer_monthly_activity_v01.parquet`라는
별도 계약 파일을 기다리다가, 그 파일이 저장소에 없어서 빈 상태로 두고 있던 자리다
([`app/views/reviewer_360.py:278-294`](../archive/app_streamlit_v04/views/reviewer_360.py)).
그 계약을 v04 `sample_id` 단위로 정식 구현한 파일이
`reviewer_monthly_activity_v04.parquet`이다. React는 이 파일을 JSON으로 변환해
사용한다. Streamlit 화면 연결은 이번 범위에 포함하지 않는다.

### 4-2. 처리 단계

1. 파이프라인이 두 리뷰 파일을 합쳐 해당 `sample_id`의 리뷰만 남긴다.
2. **`comparison_year`~`selection_year` 구간만** 남긴다(예: 2017-01~2018-12).
   `target_year`(검증 연도, 2019)는 의도적으로 제외한다 — 이 탭은 "검증 정답 표시"
   토글 뒤에 숨겨진 사후 검증 탭과 달리 항상 보이는 탭이라, 여기에 검증 연도 활동을
   넣으면 아직 공개되면 안 되는 사후 결과가 새어나가는 셈이 된다(시간 누수 방지 원칙,
   `AGENTS.md` 3절).
3. 월(`YYYY-MM`) 단위로 묶어서 그 달의 **리뷰 수**(`reviewCount`)와 **고유 음식점
   수**(`uniqueBusinessCount`)를 집계한다.
4. 활동이 있던 달만 JSON에 저장한다(용량 절약 — 6,533명 전원의 24개월치를 빠짐없이
   저장하면 파일이 훨씬 커짐). 활동 없는 달은 프런트엔드에서 0으로 채워 연속된 월
   축으로 그린다(`buildSeries()`, `MonthlyActivityChart.jsx`).

### 4-3. 검증

특정 리뷰어 2명(순위 1위, 2위)에 대해 월별 타임라인 합계와 "활동 변화" 탭의
`recent_review_count`(14건, 10건)가 정확히 일치함을 확인했다 — 3절의 이중 소스 버그를
고친 뒤의 결과다.

---

## 5. Trust Center — v02/v03 이전 모델 비교

화면: `/trust`의 "성능과 Top-K", "피처 근거" 탭 안 접기(expander) 섹션
([TrustCenterPage.jsx](../app/src/pages/TrustCenterPage.jsx))
내보내기 함수: [`export_trust()`](../scripts/export_frontend_data.py) (`scripts/export_frontend_data.py:526`),
`_multiclass_trust_block()`, `_v02_block()`, `_v03_top20()`

### 5-1. 원천 데이터

v04 기본 지표와 달리, 이 섹션은 v04 프로파일이 아니라 **과거 모델 세대의 리포트
파일을 그대로** 읽는다. 전부 `reports/tables/` 밑에 있다.

| 파일 | 모델 세대 | 용도 |
|---|---|---|
| `multiclass_validation_results_v03.csv` | v03(3클래스, 이전 코호트) | Macro F1/PR-AUC/ROC-AUC, 클래스별 성능 |
| `multiclass_top_k_performance_v03.csv` | v03 | Top-K 커브, 상위 20% 지표 |
| `multiclass_confusion_matrix_v03.csv` | v03 | 혼동 행렬 |
| `final_feature_importance_v03.csv` | v03 | 피처 중요도 |
| `final_feature_group_importance_v03.csv` | v03 | 피처 그룹 중요도 |
| `validation_test_comparison_v02.csv` | v02(이진 이탈 분류) | PR-AUC/ROC-AUC/Recall/Precision, Validation vs Test 비교 |
| `final_test_top_k_performance_v02.csv` | v02 | Top-K 커브(이진 모델 스키마 — `target_rate_pct`, `precision_at_k` 등) |
| `final_feature_importance_v02.csv` | v02 | 피처 중요도 |
| `final_feature_group_importance_v02.csv` | v02 | 피처 그룹 중요도 |

### 5-2. 처리 단계

- **v03**: 화면에서 사용하는 3클래스 지표 컬럼이 v04와 호환되므로
  처리 로직(`_multiclass_trust_block()`)을 재사용한다. 원본 CSV의 부가 컬럼까지
  완전히 같은 것은 아니다. 별도로 `_v03_top20()`이 "상위 20%" 요약(대상자 수,
  포착 인원, Precision/Recall/Lift)만 추가로 뽑는다.
- **v02**: 이진 이탈 분류 모델이라 3클래스와 지표 체계 자체가 다르다(`_v02_block()`).
  `validation_test_comparison_v02.csv`에서 `dataset == "Test"` 행을 기본 지표로 쓰고,
  Validation/Test 두 행 전체는 비교 차트(`ModelComparisonChart`)용으로 남긴다.
- 두 세대 모두 **접혀 있는 상태(expander)로 표시**되고, v04 기본 수치와 절대 섞이지
  않는다 — Streamlit `trust_center.py`의 원래 구성을 그대로 따른 것이다
  (`archive/app_streamlit_v04/views/trust_center.py:146-434`).

### 5-3. 검증

v03 Macro F1 0.575·Test 표본 4,157명·상위 20% 832명/773명/92.9%/29.5%/1.48배,
v02 PR-AUC 0.426·Recall 71.3% 등 브라우저에서 렌더링된 값이 CSV 원본과 일치함을
확인했다(2026-07-28).

---

## 6. 재생성 방법

원천 리뷰·음식점 데이터가 바뀌면 파생 Parquet을 먼저 재생성한다. 이후 모델
프로파일, 파생 Parquet, 리포트 CSV 중 하나라도 바뀌면 React JSON을 갱신한다.

```powershell
.\.venv\Scripts\python.exe pipeline\v04\derived_reviewer_activity.py
.\.venv\Scripts\python.exe scripts\export_frontend_data.py
```

파생 파일의 경로나 컬럼이 바뀌면 데이터 계약, 파이프라인, DB 로더,
`scripts/export_frontend_data.py`를 함께 갱신해야 한다.
