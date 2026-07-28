import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from utils.charts import monthly_line
from utils.data_loader import load_bundle, load_observation
from utils.ui import hero, inject_css, metric_card, section_header, sidebar_context


st.set_page_config(page_title="리뷰어 탐색기", page_icon="🔎", layout="wide")
inject_css()
bundle, is_demo, root = load_bundle()
sidebar_context(is_demo)
features = bundle["features"]
observation = bundle.get("observation")
if observation is None:
    observation = load_observation(str(root))

hero("REVIEWER EXPLORER", "한 명의 루틴을 시간순으로 읽기", "익명 리뷰어의 2017년 기준 활동과 2018년 변화를 실제 월별 기록과 지도에서 확인합니다.")

available_users = sorted(set(features["user_id"]) & set(observation["user_id"]))
if not available_users:
    st.error("리뷰어 관찰 데이터를 찾지 못했습니다.")
    st.stop()

query = st.text_input("사용자 ID 검색", placeholder="user_id 일부를 입력하세요")
filtered_users = [user for user in available_users if query.lower() in user.lower()][:300]
selected_user = st.selectbox("리뷰어 선택", filtered_users or available_users[:300])
row = features.loc[features["user_id"] == selected_user].iloc[0]

columns = st.columns(4)
values = [
    ("2017 리뷰", row.get("baseline_review_count", "-"), "기준 활동"),
    ("2018 리뷰", row.get("recent_review_count", "-"), "최근 활동"),
    ("최근 공백", f"{row.get('recent_recency_days', float('nan')):.1f}일", "2018년 말 기준"),
    ("2019 실제 결과", "이탈" if int(row["churn"]) == 1 else "유지", "검증용 정답"),
]
for container, (label, value, note) in zip(columns, values):
    with container:
        metric_card(label, str(value), note)

left, right = st.columns([1.15, 0.85], gap="large")
with left:
    st.plotly_chart(monthly_line(observation, selected_user), width="stretch")
with right:
    section_header("FEATURE SNAPSHOT", "활동 변화 요약")
    display_columns = [
        "review_count_decline_rate",
        "active_month_decline_rate",
        "recent_mean_interval_days",
        "mean_interval_increase_days",
        "recent_recency_days",
        "log_p90_radius_decline",
        "mean_rating_change",
    ]
    snapshot = pd.DataFrame(
        {"피처": [column for column in display_columns if column in row.index],
         "값": [row[column] for column in display_columns if column in row.index]}
    )
    st.dataframe(snapshot, width="stretch", hide_index=True)

section_header("MAP", "리뷰 음식점 위치", "지도는 선택한 익명 리뷰어의 관찰 기간 기록만 표시합니다.")
user_reviews = observation.loc[observation["user_id"] == selected_user].copy()
if {"latitude", "longitude"}.issubset(user_reviews.columns) and not user_reviews.empty:
    map_frame = user_reviews[["latitude", "longitude"]].dropna().rename(columns={"latitude": "lat", "longitude": "lon"})
    st.map(map_frame, width="stretch")
else:
    st.info("좌표 피처가 없어 지도를 표시할 수 없습니다.")

st.warning("이 화면의 이탈 여부는 2019년 실제 결과입니다. 아직 모델 위험 점수나 예측 확률이 아닙니다.")
