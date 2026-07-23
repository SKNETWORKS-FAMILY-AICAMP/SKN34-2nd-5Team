import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from utils.charts import cohort_funnel
from utils.data_loader import load_bundle
from utils.ui import hero, inject_css, insight, metric_card, section_header, sidebar_context


st.set_page_config(
    page_title="Yelp Reviewer Lab",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
bundle, is_demo, root = load_bundle()
sidebar_context(is_demo)

features = bundle["features"]
metadata = bundle["metadata"]
total_users = len(features)
churn_users = int(features["churn"].sum())
churn_rate = churn_users / total_users if total_users else 0

hero(
    "POWER REVIEWER RETENTION LAB",
    "파워 리뷰어의 루틴은 언제 무너지는가",
    "2017년 파워 리뷰어의 2018년 활동 변화를 추적해 2019년 리뷰 활동 중단과 연결되는 신호를 검증합니다.",
)

columns = st.columns(4)
with columns[0]:
    metric_card("음식점 리뷰", f"{metadata['restaurant_reviews']:,}", "Restaurants 범위")
with columns[1]:
    metric_card("파워 리뷰어", f"{metadata['power_reviewers']:,}", "2017 연간 기준")
with columns[2]:
    metric_card("예측 대상", f"{total_users:,}", "2018 하반기 활동 사용자")
with columns[3]:
    metric_card("실제 이탈률", f"{churn_rate:.2%}", f"{churn_users:,}명 · 2019 리뷰 0건")

left, right = st.columns([1.15, 0.85], gap="large")
with left:
    st.plotly_chart(cohort_funnel(metadata, total_users), width="stretch")
with right:
    section_header("VALIDATED SIGNALS", "현재 가장 강한 이탈 징후")
    insight("리뷰 활동량 감소", "이탈자의 평균 리뷰 감소율은 55.65%로 유지 사용자보다 크게 나타났습니다.")
    insight("작성 주기 붕괴", "이탈자의 최근 평균 작성 간격은 47.59일, 최근 활동 공백은 93.03일입니다.", "teal")
    insight("가설을 그대로 믿지 않기", "신규 음식점 비율·카테고리 다양성·탐방 반경은 활동량 통제 후 독립적 신호가 약했습니다.")

section_header("HOW TO READ", "이 프로토타입에서 볼 수 있는 것")
tabs = st.tabs(["코호트", "핵심 신호", "가설 검증", "리뷰어 탐색"])
with tabs[0]:
    st.write("연간 파워 리뷰어 정의와 최종 3,908명 코호트가 만들어지는 과정을 확인합니다.")
with tabs[1]:
    st.write("이탈자와 유지자의 리뷰 감소율, 활동 월수, 작성 간격, 최근 공백을 비교합니다.")
with tabs[2]:
    st.write("각 피처를 채택·보조·제외로 판정한 근거와 데이터 한계를 확인합니다.")
with tabs[3]:
    st.write("익명 리뷰어 한 명을 선택해 월별 활동 변화와 음식점 좌표를 탐색합니다.")

st.caption(f"Data root: {root} · {'Demo mode' if is_demo else 'Validated v01 data'}")
