import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import gc
import duckdb

'''
환경 설정 및 설정값 로드
'''
current_path = Path.cwd().resolve()
PROJECT_ROOT = next(
    (path for path in [current_path, *current_path.parents] if (path / "data").exists()),
    None
)

if PROJECT_ROOT is None:
        raise FileNotFoundError("data 폴더를 찾을 수 없습니다. 프로젝트 루트 경로를 확인해주세요.")

CONFIG_PATH = (
    PROJECT_ROOT
    / "configs"
    / "analysis_config_v04.yaml"
)

with CONFIG_PATH.open(
    mode="r",
    encoding="utf-8"
) as file:
    config = yaml.safe_load(file)

# 코호트 버전
cohort_version = 'v05'

# 음식 관련 데이터 범위
business_scope = config[
    'business_scope'
]['scope']

# 코호트 설정
# 최소 선정 연도
minimum_selection_year = config[
    'cohort'
]['minimum_selection_year']
# 검증 선정 연도
validation_selection_year = config[
    'cohort'
]['validation_selection_year']
# 테스트 선정 연도
test_selection_year = config[
    'cohort'
]['test_selection_year']
# 파워리뷰어 최소 리뷰 수
minimum_review_count = config[
    'cohort'
]['minimum_review_count']
# 파워리뷰어 최소 활동 월 수
minimum_active_months = config[
    'cohort'
]['minimum_active_months']

# 리텐션 설정
# 유지 클래스
retained_class = config[
    'retention_state'
]['retained_class']
# 약화 클래스
weakened_class = config[
    'retention_state'
]['weakened_class']
# 중단 클래스
stopped_class = config[
    'retention_state'
]['stopped_class']

# 산출물 경로
# 코호트 마스터 경로
cohort_output = config[
    'outputs'
]['cohort']
# 모델링 데이터셋 경로
modeling_dataset_output = PROJECT_ROOT / 'data' / 'processed' / f'modeling_dataset_rolling_{cohort_version}_ml.parquet'


def process_business_data():
    '''
    음식 관련 업체 필터링
    '''
    # 1. 경로 설정
    current_path = Path.cwd().resolve()
    PROJECT_ROOT = next(
        (path for path in [current_path, *current_path.parents] if (path / "data" / "raw").exists()),
        None
    )
    
    if PROJECT_ROOT is None:
        raise FileNotFoundError("data/raw 폴더를 찾을 수 없습니다. 프로젝트 루트 경로를 확인해주세요.")

    RAW_DIR = PROJECT_ROOT / "data" / "raw"
    INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
    
    # interim 디렉토리 생성
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    
    BUSINESS_JSON_PATH = RAW_DIR / "yelp_academic_dataset_business.json"
    RESTAURANT_OUT_PATH = INTERIM_DIR / "restaurant_businesses.parquet"
    CULINARY_OUT_PATH = INTERIM_DIR / "additional_culinary_businesses_v02.parquet"

    # 2. 유지할 컬럼 및 미식 방문형 카테고리 정의
    COLUMNS_TO_KEEP = [
        'business_id', 'name', 'address', 'city', 'state', 
        'postal_code', 'latitude', 'longitude', 'stars', 
        'review_count', 'is_open', 'categories'
    ]
    
    CULINARY_VISIT_CATEGORIES = {
        "Cafes", "Coffee & Tea", "Ice Cream & Frozen Yogurt", 
        "Desserts", "Bakeries", "Juice Bars & Smoothies", 
        "Donuts", "Cupcakes", "Food Trucks", "Bubble Tea", "Shaved Ice"
    }

    print("Business 원본 데이터를 불러오는 중...")
    business_df = pd.read_json(BUSINESS_JSON_PATH, lines=True)
    
    # 3. 카테고리 전처리 (결측치 처리 및 리스트화)
    business_df["category_list"] = (
        business_df["categories"]
        .fillna("")
        .str.split(", ")
    )

    # 4. 필터링 마스크 생성
    # 4-1. 핵심 음식점 (Restaurants)
    is_restaurant = business_df["category_list"].apply(lambda x: "Restaurants" in x)
    
    # 4-2. Food Only (Restaurants는 아니지만 Food인 경우)
    is_food = business_df["category_list"].apply(lambda x: "Food" in x)
    is_food_only = is_food & ~is_restaurant
    
    # 4-3. 미식 방문형 (Culinary Visit 대상 카테고리를 포함하는 경우)
    is_culinary_visit = business_df["category_list"].apply(
        lambda x: bool(set(x) & CULINARY_VISIT_CATEGORIES)
    )

    # 5. 데이터프레임 분리 및 컬럼 선택
    print("조건에 맞는 업체를 필터링 중...")
    restaurant_business_df = business_df.loc[is_restaurant, COLUMNS_TO_KEEP].reset_index(drop=True)
    
    additional_culinary_df = business_df.loc[
        (is_food_only & is_culinary_visit), COLUMNS_TO_KEEP
    ].reset_index(drop=True)

    # 6. 결과 저장
    print(f"음식점 데이터 저장 중... (총 {len(restaurant_business_df):,}건)")
    restaurant_business_df.to_parquet(RESTAURANT_OUT_PATH, index=False)
    
    print(f"추가 미식 방문형 데이터 저장 중... (총 {len(additional_culinary_df):,}건)")
    additional_culinary_df.to_parquet(CULINARY_OUT_PATH, index=False)

    print("✅ 음식 관련 업체 필터링 및 저장 완료")
    print(f"- Restaurants: {RESTAURANT_OUT_PATH}")
    print(f"- Additional Culinary: {CULINARY_OUT_PATH}")


def extract_reviews():
    '''
    필터링된 업체의 리뷰
    '''
    # 1. 경로 설정
    current_path = Path.cwd().resolve()
    PROJECT_ROOT = next(
        (path for path in [current_path, *current_path.parents] if (path / "data" / "raw").exists()),
        None
    )
    
    if PROJECT_ROOT is None:
        raise FileNotFoundError("data/raw 폴더를 찾을 수 없습니다. 프로젝트 루트 경로를 확인해주세요.")

    RAW_DIR = PROJECT_ROOT / "data" / "raw"
    INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
    
    REVIEW_JSON_PATH = RAW_DIR / "yelp_academic_dataset_review.json"
    
    # 선행 파일 (이전 단계에서 생성)
    BUSINESS_REST_PATH = INTERIM_DIR / "restaurant_businesses.parquet"
    BUSINESS_CUL_PATH = INTERIM_DIR / "additional_culinary_businesses_v02.parquet"
    
    # 생성할 결과 파일
    OUT_REST_PATH = INTERIM_DIR / "restaurant_reviews.parquet"
    OUT_CUL_PATH = INTERIM_DIR / "additional_culinary_reviews_v02.parquet"

    # 2. 유지할 컬럼 정의
    COLUMNS_TO_KEEP = [
        'review_id', 'user_id', 'business_id', 'stars', 
        'useful', 'funny', 'cool', 'date'
    ]

    # 3. 대상 업체(business_id) 목록 로드
    print("대상 업체(Business ID) 목록을 불러오는 중...")
    try:
        rest_bids = set(pd.read_parquet(BUSINESS_REST_PATH, columns=['business_id'])['business_id'])
        cul_bids = set(pd.read_parquet(BUSINESS_CUL_PATH, columns=['business_id'])['business_id'])
    except FileNotFoundError:
        print("❌ 에러: 선행 업체 데이터 파일이 없습니다. 01번 비즈니스 필터링을 먼저 실행해주세요.")
        return

    print(f" - 핵심 음식점 업체 수: {len(rest_bids):,}개")
    print(f" - 추가 미식 업체 수: {len(cul_bids):,}개")

    # 4. 리뷰 데이터 청크 단위 처리 (메모리 최적화)
    print("\n대용량 리뷰 데이터(JSON) 추출을 시작합니다. 이 작업은 다소 시간이 소요될 수 있습니다.")
    
    rest_reviews_list = []
    cul_reviews_list = []
    
    chunk_size = 100_000  # 한 번에 10만 줄씩 읽기
    chunk_count = 0
    
    # JSON 파일을 chunk 단위로 읽기
    for chunk in pd.read_json(REVIEW_JSON_PATH, lines=True, chunksize=chunk_size):
        chunk_count += 1
        
        # 필요한 컬럼만 선택
        chunk = chunk[COLUMNS_TO_KEEP]
        
        # 날짜 타입 변환 (메모리 효율 및 후속 분석 용이성)
        chunk['date'] = pd.to_datetime(chunk['date'])
        
        # 각 그룹별 조건에 맞는 리뷰 필터링
        rest_chunk = chunk[chunk['business_id'].isin(rest_bids)]
        cul_chunk = chunk[chunk['business_id'].isin(cul_bids)]
        
        rest_reviews_list.append(rest_chunk)
        cul_reviews_list.append(cul_chunk)
        
        if chunk_count % 10 == 0:
            print(f" - {chunk_count * chunk_size:,}번째 행(Row) 처리 중...")
            
    # 5. 분할 처리된 리스트를 하나의 데이터프레임으로 병합
    print("\n데이터 추출 완료, 하나의 파일로 병합 중...")
    rest_reviews_df = pd.concat(rest_reviews_list, ignore_index=True)
    cul_reviews_df = pd.concat(cul_reviews_list, ignore_index=True)
    
    # 메모리 정리 (더 이상 필요 없는 리스트 삭제)
    del rest_reviews_list, cul_reviews_list
    gc.collect()

    # 6. 결과 저장
    print(f"\n음식점 리뷰 데이터 저장 중... (총 {len(rest_reviews_df):,}건)")
    rest_reviews_df.to_parquet(OUT_REST_PATH, index=False)
    
    print(f"추가 미식 방문형 리뷰 데이터 저장 중... (총 {len(cul_reviews_df):,}건)")
    cul_reviews_df.to_parquet(OUT_CUL_PATH, index=False)

    print("\n✅ 모든 리뷰 데이터 전처리 및 저장 완료")
    print(f"- Restaurants Reviews: {OUT_REST_PATH}")
    print(f"- Additional Culinary Reviews: {OUT_CUL_PATH}")


def create_cohort_master():
    '''
    코호트 마스터 생성
    (파워 리뷰어 후보 명단, 연도 구조, 연도별 리뷰 수, 활동 월 수, 메타데이터, 타겟)
    '''
    # 1. 경로 설정
    current_path = Path.cwd().resolve()
    PROJECT_ROOT = next(
        (path for path in [current_path, *current_path.parents] if (path / "data" / "interim").exists()),
        None
    )
    
    if PROJECT_ROOT is None:
        raise FileNotFoundError("data/interim 폴더를 찾을 수 없습니다. 프로젝트 최상위 경로에서 실행해주세요.")

    INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
    ROLLING_DIR = INTERIM_DIR / "rolling"
    ROLLING_DIR.mkdir(parents=True, exist_ok=True)

    try:
        COHORT_PATH = PROJECT_ROOT / cohort_output
    except KeyError:
        # yaml에 outputs 항목이 누락되었을 경우 기본 경로 설정
        COHORT_PATH = PROJECT_ROOT / "data" / "interim" / "rolling" / "culinary_rolling_cohort_master_v04.parquet"
    
    # 선행 파일 경로
    RESTAURANT_REVIEW_PATH = INTERIM_DIR / "restaurant_reviews.parquet"
    ADDITIONAL_REVIEW_PATH = INTERIM_DIR / "additional_culinary_reviews.parquet"

    # 2. DuckDB SQL을 활용한 고속 집계 (메모리 최적화)
    print("DuckDB를 활용하여 대용량 리뷰 데이터 병합 및 연도별 집계를 시작합니다...")
    
    con = duckdb.connect()
    
    # 두 개의 Parquet 파일을 가상으로 합치는 쿼리
    review_union_sql = f'''(
        SELECT review_id, user_id, business_id, CAST(date AS TIMESTAMP) AS review_ts
        FROM read_parquet('{RESTAURANT_REVIEW_PATH.as_posix()}')
        UNION ALL
        SELECT review_id, user_id, business_id, CAST(date AS TIMESTAMP) AS review_ts
        FROM read_parquet('{ADDITIONAL_REVIEW_PATH.as_posix()}')
    )'''

    # Y-1(비교), Y(선정), Y+1(타겟) 연도의 활동을 집계하는 핵심 쿼리
    cohort_sql = f'''
    WITH reviews AS (SELECT * FROM {review_union_sql}),
    yearly AS (
        SELECT user_id, YEAR(review_ts) AS activity_year,
               COUNT(*) AS review_count,
               COUNT(DISTINCT DATE_TRUNC('month', review_ts)) AS active_months
        FROM reviews
        WHERE YEAR(review_ts) BETWEEN {minimum_selection_year - 1} AND {test_selection_year + 1}
        GROUP BY user_id, activity_year
    ),
    selection_years AS (
        SELECT * FROM RANGE({minimum_selection_year}, {test_selection_year + 1}) t(selection_year)
    ),
    candidates AS (
        SELECT y.selection_year, a.user_id,
               a.review_count AS recent_review_count,
               a.active_months AS recent_active_months
        FROM selection_years y
        JOIN yearly a
          ON a.activity_year = y.selection_year
         AND a.review_count >= {minimum_review_count}
         AND a.active_months >= {minimum_active_months}
    )
    SELECT c.user_id,
           c.selection_year - 1 AS comparison_year,
           c.selection_year,
           c.selection_year + 1 AS target_year,
           COALESCE(b.review_count, 0) AS baseline_review_count,
           COALESCE(b.active_months, 0) AS baseline_active_months,
           c.recent_review_count,
           c.recent_active_months,
           COALESCE(t.review_count, 0) AS target_review_count,
           COALESCE(t.active_months, 0) AS target_active_months
    FROM candidates c
    LEFT JOIN yearly b
      ON b.user_id = c.user_id AND b.activity_year = c.selection_year - 1
    LEFT JOIN yearly t
      ON t.user_id = c.user_id AND t.activity_year = c.selection_year + 1
    ORDER BY c.selection_year, c.user_id
    '''

    print("코호트 후보 추출 및 타겟 데이터 생성 중...")
    cohort_df = con.execute(cohort_sql).fetchdf()

    # 3. 데이터 타입 최적화
    integer_columns = [
        'comparison_year', 'selection_year', 'target_year',
        'baseline_review_count', 'baseline_active_months',
        'recent_review_count', 'recent_active_months',
        'target_review_count', 'target_active_months'
    ]
    cohort_df[integer_columns] = cohort_df[integer_columns].astype('int32')

    # 4. 파생 변수(라벨, 식별자, 스플릿) 생성
    print("정답 라벨(Retention State) 및 메타데이터 생성 중...")
    
    # 식별자
    cohort_df['sample_id'] = cohort_df['user_id'] + '_' + cohort_df['selection_year'].astype(str)
    # 전년도 활동 존재 여부
    cohort_df['prior_activity_available'] = cohort_df['baseline_review_count'].gt(0).astype('int8')
    
    # 3클래스 리텐션 상태 정의 (2: 중단, 1: 약화, 0: 유지)
    cohort_df['retention_state'] = np.select(
        [
            cohort_df['target_review_count'].eq(0), # 중단 조건
            cohort_df['target_review_count'].lt(minimum_review_count) | cohort_df['target_active_months'].lt(minimum_active_months), # 약화 조건
        ],
        [stopped_class, weakened_class],
        default=retained_class # 유지
    ).astype('int8')
    
    # 이전 이진 분류 호환용 이탈(churn) 변수
    cohort_df['churn'] = cohort_df['retention_state'].eq(2).astype('int8')
    
    # 스코프 및 스플릿 정보
    cohort_df['scope'] = business_scope
    cohort_df['split_v04'] = np.select(
        [
            cohort_df['selection_year'].le(2016),
            cohort_df['selection_year'].eq(2017),
            cohort_df['selection_year'].eq(2018),
        ],
        ['train', 'validation', 'test'],
        default='excluded',
    )

    # 5. 최종 컬럼 정렬 및 저장
    FINAL_COLUMNS = [
        'sample_id', 'user_id', 'comparison_year', 'selection_year', 'target_year', 
        'baseline_review_count', 'baseline_active_months', 
        'recent_review_count', 'recent_active_months', 
        'target_review_count', 'target_active_months', 
        'prior_activity_available', 'retention_state', 'churn', 'scope', 'split_v04'
    ]
    
    cohort_df = cohort_df[FINAL_COLUMNS]

    print(f"코호트 마스터 데이터 저장 중... (총 {len(cohort_df):,}건)")
    cohort_df.to_parquet(COHORT_PATH, index=False)

    print("\n✅ 코호트 마스터 생성 및 저장 완료")
    print(f"- 저장 경로: {COHORT_PATH}")
    
    # 데이터 검증용 출력
    print("\n[생성된 데이터 요약]")
    print(cohort_df.groupby(['selection_year', 'retention_state']).size().unstack(fill_value=0))

# create_modeling_dataset_with_config 헬퍼 함수
def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """0으로 나누는 에러를 방지하고 무한대를 NaN으로 처리하는 안전한 나눗셈 함수"""
    result = numerator.astype(float).div(denominator.replace(0, np.nan).astype(float))
    return result.replace([np.inf, -np.inf], np.nan)

def parse_elite_years(elite_val):
        if not elite_val or pd.isna(elite_val): return []
        parsed_years = []
        for token in [t.strip() for t in str(elite_val).split(',')]:
            if not token or token.lower() in ('none', 'null'): continue
            try:
                year = int(token)
                if year < 100: year += 2000
                parsed_years.append(year)
            except ValueError: continue
        return parsed_years

def calculate_group2_features(y_series):
        y = y_series.values
        slope = np.polyfit(np.arange(1, 7), y, 1)[0] if np.sum(y) > 0 else 0.0
        recent3m_vs_prev3m = np.sum(y[3:6]) / (np.sum(y[0:3]) + 1e-5)
        return pd.Series({
            'review_count_slope_6m': slope,
            'review_recent3m_vs_prev3m': recent3m_vs_prev3m,
            'inactive_month_count_6m': np.sum(y == 0),
            'inactive_month_count_3m': np.sum(y[3:6] == 0)
        })

def calculate_slope(y_series):
        y = y_series.values
        return np.polyfit(np.arange(1, 7), y, 1)[0] if np.sum(y) > 0 else 0.0

def create_modeling_dataset_with_config():
    '''
    모델링 데이터셋 생성
    (모델 입력 피처 43개 + 메타데이터, 타겟 컬럼 12개)
    '''
    # =========================================================================
    # 1. 산출물 경로 변수화
    # =========================================================================
    try:
        COHORT_PATH = PROJECT_ROOT / cohort_output
        MODELING_OUTPUT_PATH = PROJECT_ROOT / modeling_dataset_output
    except KeyError:
        # yaml에 outputs 항목이 누락되었을 경우 기본 경로 설정
        COHORT_PATH = PROJECT_ROOT / "data" / "interim" / "rolling" / "culinary_rolling_cohort_master_v04.parquet"
        MODELING_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "modeling_dataset_rolling_v04.parquet"

    # 상위 폴더가 없다면 자동 생성
    MODELING_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 기타 선행 데이터 파일 경로
    REST_REVIEW_PATH = PROJECT_ROOT / "data" / "interim" / "restaurant_reviews.parquet"
    ADD_REVIEW_PATH = PROJECT_ROOT / "data" / "interim" / "additional_culinary_reviews.parquet"

    # =========================================================================
    # 2. 코호트 마스터 로드
    # =========================================================================
    print("코호트 마스터 데이터를 불러오는 중...")
    try:
        cohort_df = pd.read_parquet(COHORT_PATH)
    except FileNotFoundError:
        print(f"❌ 에러: {COHORT_PATH} 파일을 찾을 수 없습니다. 선행 코드를 먼저 실행해주세요.")
        return
    
    # =========================================================================
    # [엘리트/가입 연차 피처] (v05 피처 추가)
    # =========================================================================
    print("User 데이터 로드 및 엘리트/가입 연차 피처 생성 중...")
    USER_JSON_PATH = PROJECT_ROOT / "data" / "raw" / "yelp_academic_dataset_user.json"
    user_df = pd.read_json(USER_JSON_PATH, lines=True)[['user_id', 'yelping_since', 'elite']]
    
    user_df['yelping_since'] = pd.to_datetime(user_df['yelping_since'])
    user_df['join_year'] = user_df['yelping_since'].dt.year

    user_features = cohort_df[['sample_id', 'user_id', 'selection_year']].merge(user_df, on='user_id', how='left')
    user_features['active_years'] = user_features['selection_year'] - user_features['join_year']

    user_features['parsed_elite_years'] = user_features['elite'].apply(parse_elite_years)
    years_since_last_elite = []
    
    for s_year, elite_years in zip(user_features['selection_year'], user_features['parsed_elite_years']):
        if isinstance(elite_years, list) and len(elite_years) > 0:
            valid_years = [y for y in elite_years if y <= s_year]
            years_since_last_elite.append(s_year - max(valid_years) if valid_years else -1)
        else:
            years_since_last_elite.append(-1)
            
    user_features['years_since_last_elite'] = years_since_last_elite
    user_features = user_features[['sample_id', 'active_years', 'years_since_last_elite']]

    # =========================================================================
    # [피처 그룹 1] 활동량 (Activity) 피처 생성 - 15개
    # =========================================================================
    print("활동량 피처 생성 중...")
    activity_df = cohort_df[['sample_id', 'user_id', 'selection_year', 'baseline_review_count', 'baseline_active_months', 'recent_review_count', 'recent_active_months']].copy()
    
    activity_df['baseline_reviews_per_active_month'] = safe_ratio(activity_df['baseline_review_count'], activity_df['baseline_active_months'])
    activity_df['recent_reviews_per_active_month'] = safe_ratio(activity_df['recent_review_count'], activity_df['recent_active_months'])
    activity_df['review_count_diff'] = activity_df['recent_review_count'] - activity_df['baseline_review_count']
    activity_df['review_count_ratio'] = safe_ratio(activity_df['recent_review_count'], activity_df['baseline_review_count'])
    activity_df['review_count_decline_rate'] = safe_ratio(activity_df['baseline_review_count'] - activity_df['recent_review_count'], activity_df['baseline_review_count'])
    activity_df['active_month_diff'] = activity_df['recent_active_months'] - activity_df['baseline_active_months']
    activity_df['active_month_ratio'] = safe_ratio(activity_df['recent_active_months'], activity_df['baseline_active_months'])
    activity_df['active_month_decline_rate'] = safe_ratio(activity_df['baseline_active_months'] - activity_df['recent_active_months'], activity_df['baseline_active_months'])
    activity_df['reviews_per_active_month_diff'] = activity_df['recent_reviews_per_active_month'] - activity_df['baseline_reviews_per_active_month']
    activity_df['reviews_per_active_month_ratio'] = safe_ratio(activity_df['recent_reviews_per_active_month'], activity_df['baseline_reviews_per_active_month'])
    activity_df['reviews_per_active_month_decline_rate'] = safe_ratio(activity_df['baseline_reviews_per_active_month'] - activity_df['recent_reviews_per_active_month'], activity_df['baseline_reviews_per_active_month'])

    # =========================================================================
    # DuckDB를 활용한 리뷰 쿼리 (공통 구간)
    # =========================================================================
    print("DuckDB를 이용해 작성 간격 및 음식점 탐색 피처 추출 중 (시간 소요)...")
    con = duckdb.connect()
    review_union_sql = f'''(
        SELECT review_id, user_id, business_id, CAST(date AS TIMESTAMP) AS review_ts
        FROM read_parquet('{REST_REVIEW_PATH.as_posix()}')
        UNION ALL
        SELECT review_id, user_id, business_id, CAST(date AS TIMESTAMP) AS review_ts
        FROM read_parquet('{ADD_REVIEW_PATH.as_posix()}')
    )'''
    
    cohort_users = cohort_df[['user_id']].drop_duplicates()
    con.register('cohort_users', cohort_users)
    
    # 2009년(minimum_selection_year - 1)부터 2018년(test_selection_year)까지 필터링
    period_reviews_sql = f'''
    WITH reviews AS (SELECT * FROM {review_union_sql})
    SELECT r.user_id, r.business_id, r.review_ts, YEAR(r.review_ts) AS review_year
    FROM reviews r
    JOIN cohort_users u ON u.user_id = r.user_id
    WHERE YEAR(r.review_ts) BETWEEN {minimum_selection_year - 1} AND {test_selection_year}
    '''
    period_reviews = con.execute(period_reviews_sql).fetchdf()
    period_reviews['review_ts'] = pd.to_datetime(period_reviews['review_ts'])
    period_reviews['review_year'] = period_reviews['review_year'].astype('int16')

    # 코호트 Y-1(baseline)과 Y(recent) 리뷰 분리 매핑
    sample_years = cohort_df[['sample_id', 'user_id', 'comparison_year', 'selection_year']]
    
    baseline_reviews = period_reviews.merge(
        sample_years, left_on=['user_id', 'review_year'], right_on=['user_id', 'comparison_year'], how='inner'
    )[['sample_id', 'user_id', 'selection_year', 'business_id', 'review_ts']]
    baseline_reviews['period'] = 'baseline'
    
    recent_reviews = period_reviews.merge(
        sample_years, left_on=['user_id', 'review_year'], right_on=['user_id', 'selection_year'], how='inner'
    )[['sample_id', 'user_id', 'selection_year', 'business_id', 'review_ts']]
    recent_reviews['period'] = 'recent'
    
    sample_period_reviews = pd.concat([baseline_reviews, recent_reviews], ignore_index=True)
    sample_period_reviews = sample_period_reviews.sort_values(['sample_id', 'period', 'review_ts'])

    # =========================================================================
    # [피처 그룹 2] 리뷰 작성 간격 (Interval) 피처 생성 - 13개
    # =========================================================================
    sample_period_reviews['interval_days'] = sample_period_reviews.groupby(['sample_id', 'period'])['review_ts'].diff().dt.total_seconds() / 86400
    
    interval_summary = sample_period_reviews.groupby(['sample_id', 'period'], as_index=False).agg(
        mean_interval_days=('interval_days', 'mean'),
        median_interval_days=('interval_days', 'median'),
        max_interval_days=('interval_days', 'max'),
        last_review_date=('review_ts', 'max'),
    )
    
    interval_summary = interval_summary.merge(cohort_df[['sample_id', 'selection_year']], on='sample_id', how='left')
    interval_summary['period_end_year'] = np.where(interval_summary['period'] == 'baseline', interval_summary['selection_year'], interval_summary['selection_year'] + 1)
    interval_summary['period_end_date'] = pd.to_datetime(interval_summary['period_end_year'].astype(str) + '-01-01')
    interval_summary['recency_days'] = (interval_summary['period_end_date'] - interval_summary['last_review_date']).dt.total_seconds() / 86400

    def get_interval_frame(period, prefix):
        frame = interval_summary[interval_summary['period'] == period][['sample_id', 'mean_interval_days', 'median_interval_days', 'max_interval_days', 'recency_days']].copy()
        return frame.rename(columns={
            'mean_interval_days': f'{prefix}_mean_interval_days', 'median_interval_days': f'{prefix}_median_interval_days',
            'max_interval_days': f'{prefix}_max_interval_days', 'recency_days': f'{prefix}_recency_days'
        })

    interval_df = cohort_df[['sample_id', 'user_id', 'selection_year']].merge(get_interval_frame('baseline', 'baseline'), on='sample_id', how='left')
    interval_df = interval_df.merge(get_interval_frame('recent', 'recent'), on='sample_id', how='left')
    
    interval_df['recent_interval_available'] = cohort_df['recent_review_count'].ge(2).astype('int8').to_numpy()
    interval_df['mean_interval_increase_days'] = interval_df['recent_mean_interval_days'] - interval_df['baseline_mean_interval_days']
    interval_df['median_interval_increase_days'] = interval_df['recent_median_interval_days'] - interval_df['baseline_median_interval_days']
    interval_df['max_interval_increase_days'] = interval_df['recent_max_interval_days'] - interval_df['baseline_max_interval_days']
    interval_df['recency_increase_days'] = interval_df['recent_recency_days'] - interval_df['baseline_recency_days']
    interval_df['recency_vs_mean_interval'] = (
        interval_df['recent_recency_days'] / (interval_df['recent_mean_interval_days'] + 1)
    ).fillna(0.0)

    # =========================================================================
    # [피처 그룹 3] 음식점 탐색 (Business Exploration) 피처 생성 - 15개
    # =========================================================================
    first_review_sql = f'''
    WITH reviews AS (SELECT * FROM {review_union_sql})
    SELECT r.user_id, r.business_id, YEAR(MIN(r.review_ts)) AS first_review_year
    FROM reviews r
    JOIN cohort_users u ON u.user_id = r.user_id
    GROUP BY r.user_id, r.business_id
    '''
    first_review_df = con.execute(first_review_sql).fetchdf()
    first_review_df['first_review_year'] = first_review_df['first_review_year'].astype('int16')

    unique_period_business = sample_period_reviews.drop_duplicates(['sample_id', 'period', 'business_id'], keep='first').copy()
    business_sets = unique_period_business.groupby(['sample_id', 'period'])['business_id'].agg(set).unstack()
    business_sets = business_sets.reindex(cohort_df['sample_id'])
    business_sets['baseline'] = business_sets['baseline'].apply(lambda x: x if isinstance(x, set) else set())
    business_sets['recent'] = business_sets['recent'].apply(lambda x: x if isinstance(x, set) else set())

    business_df = cohort_df[['sample_id']].copy()
    business_df['baseline_unique_business_count'] = business_sets['baseline'].map(len).to_numpy()
    business_df['recent_unique_business_count'] = business_sets['recent'].map(len).to_numpy()
    business_df['recent_revisited_business_count'] = [len(a & b) for a, b in zip(business_sets['baseline'], business_sets['recent'])]
    business_df['recent_new_vs_baseline_count'] = [len(b - a) for a, b in zip(business_sets['baseline'], business_sets['recent'])]
    
    business_df['unique_business_count_diff'] = business_df['recent_unique_business_count'] - business_df['baseline_unique_business_count']
    business_df['unique_business_ratio'] = safe_ratio(business_df['recent_unique_business_count'], business_df['baseline_unique_business_count'])
    business_df['unique_business_decline_rate'] = safe_ratio(business_df['baseline_unique_business_count'] - business_df['recent_unique_business_count'], business_df['baseline_unique_business_count'])
    business_df['recent_revisit_rate'] = safe_ratio(business_df['recent_revisited_business_count'], business_df['recent_unique_business_count'])
    business_df['recent_new_vs_baseline_rate'] = safe_ratio(business_df['recent_new_vs_baseline_count'], business_df['recent_unique_business_count'])

    new_business = unique_period_business.merge(first_review_df, on=['user_id', 'business_id'], how='left')
    new_business['review_year'] = new_business['review_ts'].dt.year.astype('int16')
    new_business['is_new_business'] = new_business['review_year'].eq(new_business['first_review_year']).astype('int8')
    
    new_counts = new_business.groupby(['sample_id', 'period'])['is_new_business'].sum().unstack(fill_value=0)
    new_counts = new_counts.reindex(cohort_df['sample_id'], fill_value=0)
    
    business_df['baseline_new_business_count'] = new_counts.get('baseline', 0).astype('int32').to_numpy()
    business_df['recent_new_business_count'] = new_counts.get('recent', 0).astype('int32').to_numpy()
    business_df['baseline_new_business_rate'] = safe_ratio(business_df['baseline_new_business_count'], business_df['baseline_unique_business_count'])
    business_df['recent_new_business_rate'] = safe_ratio(business_df['recent_new_business_count'], business_df['recent_unique_business_count'])
    business_df['new_business_count_diff'] = business_df['recent_new_business_count'] - business_df['baseline_new_business_count']
    business_df['new_business_rate_decline'] = business_df['baseline_new_business_rate'] - business_df['recent_new_business_rate']

    # =========================================================================
    # [피처 그룹 4] 최근 6개월 시계열 및 신규 식당 탐색 피처 생성 (v05 피처 추가)
    # =========================================================================
    print("최근 6개월 시계열 피처 및 식당 탐색 피처 생성 중...")
    
    reviews_df1 = pd.read_parquet(REST_REVIEW_PATH, columns=['review_id', 'user_id', 'date', 'business_id'])
    reviews_df2 = pd.read_parquet(ADD_REVIEW_PATH, columns=['review_id', 'user_id', 'date', 'business_id'])
    reviews_df = pd.concat([reviews_df1, reviews_df2], ignore_index=True).drop_duplicates(subset=['review_id'])
    
    cohort_base = cohort_df[['sample_id', 'user_id', 'selection_year']].copy()
    cohort_base['base_date'] = pd.to_datetime(cohort_base['selection_year'].astype(str) + '-12-31')

    # 코호트와 조인 및 6개월 필터링
    df_merged = pd.merge(reviews_df, cohort_base, on='user_id', how='inner')
    df_merged['days_diff'] = (df_merged['base_date'] - df_merged['date']).dt.days
    df_filtered = df_merged[(df_merged['days_diff'] >= 0) & (df_merged['days_diff'] < 180)].copy()
    df_filtered['month_bin'] = 6 - (df_filtered['days_diff'] // 30)

    # 1) 리뷰수 시계열 4종 (review_count_slope_6m 등)
    monthly_counts = df_filtered.groupby(['sample_id', 'month_bin']).size().reset_index(name='review_count')
    pivot_df = monthly_counts.pivot(index='sample_id', columns='month_bin', values='review_count').fillna(0)
    for m in range(1, 7):
        if m not in pivot_df.columns: pivot_df[m] = 0
    pivot_df = pivot_df[[1, 2, 3, 4, 5, 6]]

    time_series_features = pivot_df.apply(calculate_group2_features, axis=1).reset_index()

    # 2) 고유 식당 탐색 추세선 (unique_business_slope_6m)
    ub_counts = df_filtered.groupby(['sample_id', 'month_bin'])['business_id'].nunique().reset_index(name='unique_count')
    pivot_ub = ub_counts.pivot(index='sample_id', columns='month_bin', values='unique_count').fillna(0)
    for m in range(1, 7):
        if m not in pivot_ub.columns: pivot_ub[m] = 0
    pivot_ub = pivot_ub[[1, 2, 3, 4, 5, 6]]

    pivot_ub['unique_business_slope_6m'] = pivot_ub.apply(calculate_slope, axis=1)
    time_series_features = time_series_features.merge(pivot_ub[['unique_business_slope_6m']].reset_index(), on='sample_id', how='left')

    # 3) 최근 신규 식당 탐색 후 경과 기간 (months_since_last_new_business)
    first_visits = reviews_df.groupby(['user_id', 'business_id'])['date'].min().reset_index(name='first_visit_date')
    merged_visits = pd.merge(first_visits, cohort_base, on='user_id', how='inner')
    valid_visits = merged_visits[merged_visits['first_visit_date'] <= merged_visits['base_date']].copy()
    
    last_discovery = valid_visits.groupby('sample_id')['first_visit_date'].max().reset_index(name='last_discovery_date')
    last_discovery = last_discovery.merge(cohort_base[['sample_id', 'base_date']].drop_duplicates(), on='sample_id', how='left')
    last_discovery['months_since_last_new_business'] = (last_discovery['base_date'] - last_discovery['last_discovery_date']).dt.days // 30
    
    time_series_features = time_series_features.merge(last_discovery[['sample_id', 'months_since_last_new_business']], on='sample_id', how='left')

    # =========================================================================
    # 최종 데이터 결합 및 저장
    # =========================================================================
    print("피처 결합 및 저장 중...")
    
    FINAL_COLUMNS = [
        'sample_id', 'user_id', 'comparison_year', 'selection_year', 'target_year', 
        'target_review_count', 'target_active_months', 'retention_state', 'churn', 
        'prior_activity_available', 'scope', 'split_v04', 'baseline_review_count', 
        'baseline_active_months', 'baseline_reviews_per_active_month', 'recent_review_count', 
        'recent_active_months', 'recent_reviews_per_active_month', 'review_count_diff', 
        'review_count_ratio', 'review_count_decline_rate', 'active_month_diff', 
        'active_month_ratio', 'active_month_decline_rate', 'reviews_per_active_month_diff', 
        'reviews_per_active_month_ratio', 'reviews_per_active_month_decline_rate', 
        'baseline_mean_interval_days', 'baseline_median_interval_days', 'baseline_max_interval_days', 
        'baseline_recency_days', 'recent_mean_interval_days', 'recent_median_interval_days', 
        'recent_max_interval_days', 'recent_recency_days', 'recent_interval_available', 
        'mean_interval_increase_days', 'median_interval_increase_days', 'max_interval_increase_days', 
        'recency_increase_days', 'baseline_unique_business_count', 'recent_unique_business_count', 
        'recent_revisited_business_count', 'recent_new_vs_baseline_count', 'unique_business_count_diff', 
        'unique_business_ratio', 'unique_business_decline_rate', 'recent_revisit_rate', 
        'recent_new_vs_baseline_rate', 'baseline_new_business_count', 'recent_new_business_count', 
        'baseline_new_business_rate', 'recent_new_business_rate', 'new_business_count_diff', 
        'new_business_rate_decline', 'active_years', 'years_since_last_elite', 'recency_vs_mean_interval',
        'review_count_slope_6m', 'review_recent3m_vs_prev3m', 'inactive_month_count_6m',
        'inactive_month_count_3m', 'unique_business_slope_6m', 'months_since_last_new_business'
    ]

    modeling_df = cohort_df.copy()
    
    for feature_frame in [user_features, activity_df, interval_df, business_df, time_series_features]:
        cols_to_merge = [c for c in feature_frame.columns if c not in modeling_df.columns or c == 'sample_id']
        modeling_df = modeling_df.merge(feature_frame[cols_to_merge], on='sample_id', how='left')
    
    # 병합 후 활동이 전혀 없어 생성된 결측치(NaN) 안전하게 방어 및 대체
    modeling_df['review_count_slope_6m'] = modeling_df['review_count_slope_6m'].fillna(0.0)
    modeling_df['review_recent3m_vs_prev3m'] = modeling_df['review_recent3m_vs_prev3m'].fillna(0.0)
    modeling_df['inactive_month_count_6m'] = modeling_df['inactive_month_count_6m'].fillna(6.0)
    modeling_df['inactive_month_count_3m'] = modeling_df['inactive_month_count_3m'].fillna(3.0)
    modeling_df['unique_business_slope_6m'] = modeling_df['unique_business_slope_6m'].fillna(0.0)
    modeling_df['months_since_last_new_business'] = modeling_df['months_since_last_new_business'].fillna(-1)

    modeling_df = modeling_df[FINAL_COLUMNS]

    modeling_df.to_parquet(MODELING_OUTPUT_PATH, index=False)
    
    print("\n✅ 모델링 데이터셋 생성 및 저장 완료")
    print(f"- 데이터 크기: {modeling_df.shape}")
    print(f"- 저장 경로: {MODELING_OUTPUT_PATH}")

# 전체 파이프라인 실행 함수
def run_preprocessing():
    process_business_data()
    extract_reviews()
    create_cohort_master()
    create_modeling_dataset_with_config()

# 데이터 통합 전처리 파이프라인 실행    
if __name__ == "__main__":
    run_preprocessing()