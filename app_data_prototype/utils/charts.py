from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


INK = "#17222E"
ORANGE = "#EF5B36"
TEAL = "#1F8A7A"
MUTED = "#AAB4BC"
PAPER = "rgba(0,0,0,0)"


def polish(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font={"family": "Arial, sans-serif", "color": INK},
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        legend_title_text="",
        hoverlabel={"bgcolor": "white", "font_color": INK},
    )
    fig.update_xaxes(showgrid=False, linecolor="#DED9D0")
    fig.update_yaxes(gridcolor="#E9E5DD", zeroline=False)
    return fig


def churn_donut(features: pd.DataFrame) -> go.Figure:
    counts = features["churn"].value_counts().reindex([0, 1], fill_value=0)
    fig = go.Figure(
        go.Pie(
            labels=["유지", "이탈"],
            values=counts.values,
            hole=0.68,
            marker_colors=[TEAL, ORANGE],
            textinfo="label+percent",
        )
    )
    fig.update_layout(title="2019년 실제 활동 결과")
    return polish(fig, 350)


def cohort_funnel(metadata: dict, cohort_users: int) -> go.Figure:
    labels = ["음식점 리뷰 사용자", "2017 파워 리뷰어", "최종 예측 대상"]
    values = [metadata["restaurant_users"], metadata["power_reviewers"], cohort_users]
    fig = go.Figure(
        go.Funnel(
            y=labels,
            x=values,
            textinfo="value+percent initial",
            marker={"color": ["#B7C3C8", TEAL, ORANGE]},
        )
    )
    fig.update_layout(title="분석 코호트 구성")
    return polish(fig, 340)


def group_box(features: pd.DataFrame, column: str, title: str, y_label: str) -> go.Figure:
    frame = features[["churn", column]].dropna().copy()
    if not frame.empty:
        lower, upper = frame[column].quantile([0.01, 0.99])
        frame = frame[frame[column].between(lower, upper)]
    frame["활동 결과"] = frame["churn"].map({0: "유지", 1: "이탈"})
    fig = px.box(
        frame,
        x="활동 결과",
        y=column,
        color="활동 결과",
        color_discrete_map={"유지": TEAL, "이탈": ORANGE},
        points=False,
        labels={column: y_label},
        title=title,
    )
    fig.update_layout(showlegend=False)
    return polish(fig)


def monthly_line(observation: pd.DataFrame, user_id: str) -> go.Figure:
    user = observation.loc[observation["user_id"] == user_id].copy()
    user["month"] = user["date"].dt.to_period("M").dt.to_timestamp()
    monthly = user.groupby("month", as_index=False).agg(
        review_count=("business_id", "size"),
        business_count=("business_id", "nunique"),
        mean_rating=("stars", "mean"),
    )
    fig = px.line(
        monthly,
        x="month",
        y="review_count",
        markers=True,
        title="월별 리뷰 활동",
        labels={"month": "월", "review_count": "리뷰 수"},
    )
    fig.update_traces(line_color=ORANGE, line_width=3, marker_size=7)
    fig.add_vline(x=pd.Timestamp("2018-01-01").timestamp() * 1000, line_dash="dot", line_color=TEAL)
    return polish(fig)
