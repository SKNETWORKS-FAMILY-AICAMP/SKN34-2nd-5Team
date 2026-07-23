import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from utils.charts import churn_donut, cohort_funnel, polish
from utils.data_loader import load_bundle
from utils.ui import hero, inject_css, metric_card, section_header, sidebar_context


st.set_page_config(page_title="코호트 개요", page_icon="🧭", layout="wide")
inject_css()
bundle, is_demo, _ = load_bundle()
sidebar_context(is_demo)
features = bundle["features"]
metadata = bundle["metadata"]

hero("COHORT DESIGN", "파워 리뷰어를 어떻게 정의했나", "연간 활동량과 지속성을 함께 반영하고, 예측 시점에 이미 이탈한 사용자는 제외했습니다.")

churn_users = int(features["churn"].sum())
retained_users = len(features) - churn_users
columns = st.columns(4)
with columns[0]: metric_card("2017 활동 사용자", "265,354", "음식점 리뷰 작성자")
with columns[1]: metric_card("2017 파워 리뷰어", f"{metadata['power_reviewers']:,}", "리뷰 10건 · 활동 3개월")
with columns[2]: metric_card("최종 코호트", f"{len(features):,}", "2018 하반기 활동 확인")
with columns[3]: metric_card("이탈 / 유지", f"{churn_users:,} / {retained_users:,}", "2019 실제 결과")

left, right = st.columns(2, gap="large")
with left:
    st.plotly_chart(cohort_funnel(metadata, len(features)), width="stretch")
with right:
    st.plotly_chart(churn_donut(features), width="stretch")

section_header("ANNUAL FLOW", "시간 구간", "코로나19라는 외부 충격을 피하기 위해 2019년까지의 안정 구간을 사용했습니다.")
timeline = px.timeline(
    x_start=["2017-01-01", "2018-01-01", "2018-07-01", "2019-01-01"],
    x_end=["2018-01-01", "2019-01-01", "2019-01-01", "2020-01-01"],
    y=["파워 리뷰어 선정", "루틴 변화 관찰", "최근 활동 조건", "이탈 확인"],
    color=["선정", "관찰", "관찰", "타깃"],
    color_discrete_map={"선정": "#1F8A7A", "관찰": "#F2A66F", "타깃": "#EF5B36"},
)
timeline.update_yaxes(autorange="reversed")
timeline.update_layout(showlegend=False, title="2017 → 2019 분석 설계")
st.plotly_chart(polish(timeline, 360), width="stretch")

st.info("이탈은 Yelp 탈퇴가 아니라 2019년 한 해 동안 음식점 리뷰를 작성하지 않은 상태입니다.")
