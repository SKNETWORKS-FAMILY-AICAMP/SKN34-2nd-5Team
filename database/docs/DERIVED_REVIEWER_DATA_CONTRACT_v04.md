# v04 리뷰어 권역·월별 활동 데이터 계약

React 화면에서 임시로 계산하던 권역과 월별 활동을 파이프라인 산출물로
고정한다. 두 산출물은 모델 입력이나 새 예측 결과가 아니며, 이미 확정된
v04 Test 표본의 관찰 구간 리뷰 활동을 운영 화면용으로 정리한 데이터다.

## 공통 원칙

- 표본 식별자는 `user_id`가 아니라 `sample_id`를 사용한다.
- `comparison_year`부터 `selection_year`까지의 리뷰만 사용한다.
- `target_year` 리뷰는 포함하지 않는다.
- 음식 관련 리뷰는 `restaurant_reviews`와 `additional_culinary_reviews`를
  `UNION ALL`한 범위와 동일하게 사용한다.
- 권역은 거주지·직장이 아니라 관찰된 `리뷰 활동 권역`이다.
- 동일 입력은 항상 동일 결과를 만들도록 동률 처리 순서를 고정한다.

추가 미식 리뷰의 표준 파일명은
`data/interim/additional_culinary_reviews.parquet`이다. 이전 작업에서 사용한
`additional_culinary_reviews_v02.parquet`도 입력 호환 목적으로 허용하지만,
두 파일이 모두 있으면 표준 파일명을 우선한다.

## 1. 리뷰어 권역

경로:

```text
data/processed/reviewer_region_v04.parquet
```

행 단위는 v04 최종 Test `sample_id`당 1행이며 현재 기대 행 수는 6,533이다.

| 컬럼 | 타입 | NULL | 의미 |
|---|---|---|---|
| `sample_id` | string | 불가 | 사용자-선정연도 표본 ID |
| `user_id` | string | 불가 | Yelp 리뷰어 ID |
| `state` | string | 불가 | 관찰 구간에 가장 많이 리뷰한 음식점 권역 |
| `top_city` | string | 가능 | 선택된 권역 안에서 가장 많이 리뷰한 도시 |

권역 계산:

1. 리뷰를 `business_id`로 음식점 데이터와 연결한다.
2. `sample_id + state`별 리뷰 수를 계산한다.
3. 리뷰 수 내림차순으로 하나의 권역을 선택한다. 동일 리뷰 수 동률은 기존
   v04 React export 결과와의 호환 순서를 유지한다. 현재 Test에는 동률 표본
   35명이 있으므로 이 정책을 바꾸려면 권역 집계 영향 확인이 필요하다.
4. 선택된 권역 안에서 `sample_id + city`별 리뷰 수를 계산한다.
5. 리뷰 수 내림차순, `city` 오름차순으로 `top_city`를 선택한다.

미국 주 코드뿐 아니라 실제 Yelp 리뷰 활동에 포함된 캐나다 지역 코드도
허용한다. 현재 v04 데이터에는 Alberta의 `AB`가 포함된다.

검증 조건:

- `sample_id` NULL·중복 0건
- v04 Test 프로필과 `sample_id` 집합 일치
- 같은 `sample_id`의 `user_id`가 프로필과 일치
- `state` NULL·빈 문자열 0건
- 허용되지 않은 권역 코드 0건

권역 전체의 대표 도시는 이 파일에 미리 집계하지 않는다.
`reviewer_region.top_city`를 권역별로 집계하는 DB View에서 계산한다.

## 2. 리뷰어 월별 활동

경로:

```text
data/processed/reviewer_monthly_activity_v04.parquet
```

행 단위는 `sample_id + 활동이 있었던 월`이다. 활동이 없는 월은 저장하지
않고 화면에서 0으로 채운다.

| 컬럼 | 타입 | NULL | 의미 |
|---|---|---|---|
| `sample_id` | string | 불가 | 사용자-선정연도 표본 ID |
| `year_month` | `YYYY-MM` | 불가 | 리뷰 활동 월 |
| `review_count` | unsigned integer | 불가 | 해당 월 음식 관련 리뷰 수 |
| `unique_business_count` | unsigned integer | 불가 | 해당 월 고유 음식점 수 |

검증 조건:

- `(sample_id, year_month)` NULL·중복 0건
- 모든 `sample_id`가 v04 Test 프로필에 존재
- 모든 v04 Test 표본에 최소 한 개의 활동 월 존재
- `comparison_year <= year_month.year <= selection_year`
- `review_count > 0`
- `0 < unique_business_count <= review_count`
- 표본별 `review_count` 합계가 프로필의
  `baseline_review_count + recent_review_count`와 일치

## 3. 생성 명령

```powershell
.\.venv\Scripts\python.exe pipeline\v04\derived_reviewer_activity.py
```

원본 리뷰·음식점 Parquet이 없으면 파일을 생성하지 않고 누락 경로를
명시하여 종료한다.
