import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from utils.charts import polish
from utils.data_loader import load_bundle
from utils.ui import hero, inject_css, insight, metric_card, section_header, sidebar_context


st.set_page_config(page_title="가설 검증실", page_icon="🧪", layout="wide")
inject_css()
bundle, is_demo, _ = load_bundle()
sidebar_context(is_demo)
features = bundle["features"]
decisions = bundle["decisions"].copy()

hero("HYPOTHESIS LAB", "가설은 검증하고, 약하면 버린다", "멋있어 보이는 피처보다 실제로 독립적인 정보를 제공하는 피처를 남깁니다.")

decision_counts = decisions["decision"].value_counts()
columns = st.columns(4)
for container, decision in zip(columns, ["채택", "채택 후보", "보조 후보", "제외"]):
    with container:
        metric_card(decision, str(int(decision_counts.get(decision, 0))), "피처 판정 수")

section_header("DECISIONS", "피처 판정표")
selected_decisions = st.multiselect(
    "판정 필터", sorted(decisions["decision"].dropna().unique()), default=list(decisions["decision"].dropna().unique())
)
filtered = decisions[decisions["decision"].isin(selected_decisions)]
st.dataframe(filtered, width="stretch", hide_index=True)

left, right = st.columns(2, gap="large")
with left:
    if {"review_count_decline_rate", "unique_category_decline_rate", "churn"}.issubset(features.columns):
        scatter = px.scatter(
            features,
            x="review_count_decline_rate",
            y="unique_category_decline_rate",
            color=features["churn"].map({0: "유지", 1: "이탈"}),
            opacity=0.45,
            color_discrete_map={"유지": "#1F8A7A", "이탈": "#EF5B36"},
            title="리뷰 감소와 카테고리 감소의 중복",
            labels={"review_count_decline_rate": "리뷰 감소율", "unique_category_decline_rate": "카테고리 감소율", "color": "활동 결과"},
        )
        st.plotly_chart(polish(scatter), width="stretch")
    else:
        st.info("카테고리 피처 파일을 찾지 못했습니다.")
with right:
    insight("신규 음식점 비율", "두 집단 모두 중앙값 100%로 독립적인 탐색 성향 변화가 확인되지 않았습니다.")
    insight("카테고리 다양성", "비슷한 리뷰 수 구간에서는 집단 차이가 사라져 활동량의 영향을 받은 것으로 판단했습니다.", "teal")
    insight("탐방 반경", "전체 비교에서는 축소됐지만 음식점 수 구간별 방향이 일관되지 않아 실험용으로 남겼습니다.")
    insight("리뷰 반응", "Useful·Cool·Funny는 반응 시점이 없어 미래 정보 누수 위험으로 제외했습니다.", "teal")
