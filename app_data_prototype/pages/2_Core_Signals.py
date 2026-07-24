import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from utils.charts import group_box
from utils.data_loader import load_bundle
from utils.ui import hero, inject_css, insight, metric_card, section_header, sidebar_context


st.set_page_config(page_title="핵심 이탈 신호", page_icon="📉", layout="wide")
inject_css()
bundle, is_demo, _ = load_bundle()
sidebar_context(is_demo)
features = bundle["features"]

hero("CORE SIGNALS", "리뷰 활동 루틴 붕괴", "모델링 전에 실제 데이터에서 이탈자와 유지자의 차이가 반복적으로 나타나는지 확인합니다.")

signal_specs = {
    "review_count_decline_rate": ("리뷰 감소율", "%", 100),
    "active_month_decline_rate": ("활동 월수 감소율", "%", 100),
    "recent_mean_interval_days": ("최근 평균 작성 간격", "일", 1),
    "recent_recency_days": ("최근 리뷰 공백", "일", 1),
    "mean_rating_change": ("평균 평점 변화", "점", 1),
}
available = {key: value for key, value in signal_specs.items() if key in features.columns}

summary_rows = []
for column, (label, unit, multiplier) in available.items():
    grouped = features.groupby("churn")[column].median()
    summary_rows.append(
        {
            "신호": label,
            "유지 중앙값": grouped.get(0, float("nan")) * multiplier,
            "이탈 중앙값": grouped.get(1, float("nan")) * multiplier,
            "단위": unit,
        }
    )
summary = pd.DataFrame(summary_rows)

columns = st.columns(min(4, max(1, len(summary))))
for container, row in zip(columns, summary.head(4).to_dict("records")):
    with container:
        metric_card(row["신호"], f"{row['이탈 중앙값']:.1f}{row['단위']}", f"유지 {row['유지 중앙값']:.1f}{row['단위']}")

section_header("COMPARE", "집단별 분포")
selected = st.selectbox("비교할 신호", list(available), format_func=lambda key: available[key][0])
label, unit, multiplier = available[selected]
plot_frame = features.copy()
plot_column = selected
if multiplier != 1:
    plot_column = f"__{selected}"
    plot_frame[plot_column] = plot_frame[selected] * multiplier
st.plotly_chart(
    group_box(plot_frame, plot_column, f"유지 vs 이탈 · {label}", unit),
    width="stretch",
)

left, right = st.columns(2, gap="large")
with left:
    insight("강한 신호", "리뷰 감소율·활동 월수 감소·최근 공백은 이탈자에게 일관되게 크게 나타났습니다.")
with right:
    insight("해석 주의", "차이는 인과관계가 아니라 2018년 행동과 2019년 이탈 사이의 연관성입니다.", "teal")
