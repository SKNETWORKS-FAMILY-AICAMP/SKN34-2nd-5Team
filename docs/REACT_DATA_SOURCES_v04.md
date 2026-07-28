# React 데이터 출처 (v04)

`app/`(React)가 v04 모델 산출물을 어떻게 읽고, 어떤 부분은 그대로 pass-through 하고
어떤 부분은 원천 데이터에서 직접 파생하는지 정의한다. Streamlit 쪽 데이터 계약은
[`STREAMLIT_DATA_CONTRACT.md`](STREAMLIT_DATA_CONTRACT.md) 참고 — 이 문서는 그 v04
산출물을 React가 어떻게 소비하는지 설명하는 짝문서다.

React는 자체 백엔드/API가 없다. `scripts/export_frontend_data.py`가 Streamlit의
`archive/app_streamlit_v04/core` 모듈을 그대로 불러와서, 화면별로 필요한 값을 JSON으로
내보내면(`app/src/data/*.json`, `app/public/data/reviewer-details.json`) React는 그걸
정적 파일로 읽기만 한다. 모델·프로파일이 갱신되면 재실행한다.

```bash
./venv/Scripts/python.exe scripts/export_frontend_data.py
```

---

## 1. 데이터 소비 방식 두 가지

| 방식 | 의미 | 해당 화면 |
|---|---|---|
| **pass-through** | 모델 프로파일(`final_test_retention_profiles_v04.parquet`)이나 리포트 CSV의 컬럼을 그대로, 혹은 단순 포맷팅만 거쳐 JSON으로 옮김 | 운영 홈, 리뷰어 관리, 리뷰어 상세의 활동 변화/작성 주기/사후 검증 탭, 플레이북, Trust Center의 v04 기본 지표 |
| **파생(derived)** | 모델 프로파일에 없는 값을, 원천 리뷰/음식점 데이터나 별도 리포트 파일에서 React 전용으로 새로 계산 | 콘텐츠 위험(권역 집계), 리뷰어 상세의 월별 타임라인, Trust Center의 v02/v03 이전 모델 비교 |

이 문서는 **파생** 쪽만 다룬다 — pass-through는 컬럼명만 다를 뿐 별도 로직이 없어서
문서화할 게 없다.

---

## 2. 콘텐츠 위험 — 권역별 집계

화면: `/regional` ([RegionalRiskPage.jsx](../app/src/pages/RegionalRiskPage.jsx))
내보내기 함수: [`export_regional()`](../scripts/export_frontend_data.py) (`scripts/export_frontend_data.py:745`)

### 2-1. 원천 데이터

| 파일 | 사용한 컬럼 | 용도 |
|---|---|---|
| `data/interim/restaurant_reviews.parquet` | `user_id`, `business_id`, `date` | 리뷰 원본 |
| `data/interim/additional_culinary_reviews_v02.parquet` | `user_id`, `business_id`, `date` | 리뷰 원본 — 위 파일 하나만으로는 리뷰 수가 부족함(3절 참고), 반드시 이 파일과 합쳐야 함 |
| `data/interim/restaurant_businesses.parquet` | `business_id`, `city`, `state` | 리뷰가 어느 지역 음식점에 달렸는지 매핑 |
| `final_test_retention_profiles_v04.parquet` (모델 프로파일) | `predicted_state`, `crm_target`, `comparison_year`, `selection_year` | 이미 나온 모델 예측 결과를 지역 기준으로 재집계하기 위한 값 |

### 2-2. 처리 단계

1. 두 리뷰 파일(`restaurant_reviews` + `additional_culinary_reviews_v02`)을 합쳐서 하나의
   리뷰 테이블을 만든다(`_load_all_reviews()`, `scripts/export_frontend_data.py:627`).
2. 모델의 관찰 구간(`comparison_year`~`selection_year`, 현재 v04 기준 2017~2018)에
   해당하는 리뷰만 남긴다.
3. `restaurant_businesses`와 조인해서 리뷰마다 `state`를 붙인다. `state`가 없는(조인
   실패) 리뷰는 버린다.
4. **리뷰어별로 그 구간에 가장 많이 리뷰를 남긴 `state`를 그 리뷰어의 "권역"으로
   확정한다.** 이건 거주지·직장이 아니라 순수하게 관찰된 리뷰 활동 기준이다 — city
   단위(208개)로 하면 교외가 도심에서 갈라져 나가서 의미가 흐려지므로 state로 묶는다.
5. 표시용 대표 도시(`topCity`)도 같은 방식으로, 그 권역 안에서 리뷰어가 가장 많이
   몰린 도시를 고른다.
6. 권역별로 묶어서 `predicted_state`를 집계한다 — 유지(0)/약화(1)/중단(2) 인원수,
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

`export_regional()`과 아래 4절의 `export_monthly_activity()` 둘 다
[`_load_all_reviews()`](../scripts/export_frontend_data.py) (`scripts/export_frontend_data.py:627`)를
공유해서 쓴다. 이 함수가 생긴 이유를 남겨둔다.

**발견 경위**: 월별 타임라인을 만들면서 `restaurant_reviews.parquet` 하나만으로 리뷰어별
월간 리뷰 수를 더해보니, 모델 프로파일의 `baseline_review_count` + `recent_review_count`
합계와 어긋나는 경우가 대부분이었다. 전체 6,533명 기준으로 검증한 결과:

- 정확히 일치: 36.9%
- 평균 부족분: 약 2건, 중앙값 1건, 최대 40건 부족
- 63.1%의 리뷰어가 실제보다 적게 집계됨

**원인**: `pipeline/v04/preprocessing.py`의 코호트 생성 SQL이
`restaurant_reviews.parquet`와 `additional_culinary_reviews.parquet`(리포지토리에는
`additional_culinary_reviews_v02.parquet`라는 이름으로 존재) 두 파일을 `UNION ALL`로
합쳐서 리뷰 수를 계산한다. React 쪽에서 후자를 빠뜨리고 있었다.

**수정**: 두 파일을 합쳐 읽는 `_load_all_reviews()`로 통일한 뒤 재검증하니 6,533명
전원 오차 0으로 정확히 일치했다. 이 수정은 콘텐츠 위험 화면(권역 판단은 원래도 이
버그의 영향이 적었지만 더 정확해짐)과 월별 타임라인(아래 4절, 합계가 안 맞으면 바로
눈에 띄는 화면이라 이 버그의 영향이 컸음) 양쪽에 적용됐다.

---

## 4. 리뷰어 상세 — 월별 타임라인

화면: `/reviewers/:reviewerId`의 "월별 타임라인" 탭
([ReviewerDetailPage.jsx](../app/src/pages/ReviewerDetailPage.jsx),
[MonthlyActivityChart.jsx](../app/src/components/reviewer-detail/MonthlyActivityChart.jsx))
내보내기 함수: [`export_monthly_activity()`](../scripts/export_frontend_data.py) (`scripts/export_frontend_data.py:649`)

### 4-1. 원천 데이터

| 파일 | 사용한 컬럼 | 용도 |
|---|---|---|
| `data/interim/restaurant_reviews.parquet` | `user_id`, `business_id`, `date` | 리뷰 원본 |
| `data/interim/additional_culinary_reviews_v02.parquet` | `user_id`, `business_id`, `date` | 리뷰 원본 — 3절 참고, 반드시 합쳐야 함 |
| `final_test_retention_profiles_v04.parquet` (모델 프로파일) | `user_id`, `comparison_year`, `selection_year` | 어느 리뷰어의, 어느 구간을 볼지 정하는 기준 |

이 화면은 원래 Streamlit이 `data/processed/predictions/reviewer_monthly_activity_v01.parquet`라는
별도 계약 파일을 기다리다가, 그 파일이 저장소에 없어서 빈 상태로 두고 있던 자리다
([`app/views/reviewer_360.py:278-294`](../archive/app_streamlit_v04/views/reviewer_360.py)).
그런데 이 계약 파일이 담으려던 값(리뷰 작성 월, 월별 리뷰 수, 월별 고유 음식점 수)은
이미 있는 원천 리뷰 데이터로 직접 계산 가능하다는 걸 확인해서, **React 쪽에서만**
채워 넣었다. Streamlit은 그대로 빈 상태를 유지한다(2026-07-28 결정 — Streamlit 코드는
이번 작업 범위에서 건드리지 않기로 함).

### 4-2. 처리 단계

1. 두 리뷰 파일을 합쳐서(`_load_all_reviews()`) 해당 리뷰어의 리뷰만 남긴다.
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

- **v03**: v04와 스키마가 동일한 3클래스 리포트라, v04 처리 로직(`_multiclass_trust_block()`)을
  그대로 재사용해서 지표를 뽑는다. 별도로 `_v03_top20()`이 "상위 20%" 요약(대상자 수,
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

원천 데이터, 모델 프로파일, 리포트 CSV 중 하나라도 바뀌면 아래 스크립트를 다시
실행해서 `app/src/data/*.json`, `app/public/data/reviewer-details.json`을 갱신한다.

```bash
./venv/Scripts/python.exe scripts/export_frontend_data.py
```

이 문서에 적힌 파일 경로(`data/interim/*.parquet`, `reports/tables/*.csv`)나 컬럼명이
바뀌면 `scripts/export_frontend_data.py`와 이 문서를 함께 갱신해야 한다.
