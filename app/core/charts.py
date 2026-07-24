from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.theme import COLORS


TIER_ORDER = ["긴급 관리", "집중 관리", "관찰 대상", "일반"]
TIER_COLORS = {
    "긴급 관리": COLORS["critical"],
    "집중 관리": COLORS["focus"],
    "관찰 대상": COLORS["watch"],
    "일반": COLORS["normal"],
}
GROUP_COLORS = {
    "activity": COLORS["primary"],
    "interval": COLORS["watch"],
    "business": COLORS["focus"],
}


def polish(figure: go.Figure, height: int = 390) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=48, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Pretendard, Noto Sans KR, Segoe UI, sans-serif",
            color=COLORS["ink"],
            size=11,
        ),
        title_font=dict(size=14),
        legend_title_text="",
        hoverlabel=dict(bgcolor=COLORS["surface"]),
    )
    figure.update_xaxes(
        gridcolor="rgba(102,116,125,.10)",
        linecolor="rgba(102,116,125,.12)",
        zeroline=False,
    )
    figure.update_yaxes(
        gridcolor="rgba(102,116,125,.10)",
        linecolor="rgba(102,116,125,.12)",
        zeroline=False,
    )
    return figure


def tier_distribution(frame: pd.DataFrame) -> go.Figure:
    data = frame.copy()
    figure = px.bar(
        data,
        x="risk_tier",
        y="users",
        color="risk_tier",
        text="users",
        color_discrete_map=TIER_COLORS,
        category_orders={"risk_tier": TIER_ORDER},
        custom_data=["observed_churn_rate", "lift"],
    )
    figure.update_traces(
        texttemplate="%{text:,.0f}명",
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>사용자 %{y:,.0f}명"
            "<br>실제 이탈률 %{customdata[0]:.1%}"
            "<br>Lift %{customdata[1]:.2f}배<extra></extra>"
        ),
    )
    figure.update_layout(
        title="위험 등급별 운영 대상",
        xaxis_title="",
        yaxis_title="리뷰어 수",
        showlegend=False,
    )
    return polish(figure)


def tier_churn_rate(frame: pd.DataFrame) -> go.Figure:
    data = frame.copy()
    figure = px.bar(
        data,
        x="risk_tier",
        y="observed_churn_rate",
        color="risk_tier",
        text=data["observed_churn_rate"].map(lambda value: f"{value:.1%}"),
        color_discrete_map=TIER_COLORS,
        category_orders={"risk_tier": TIER_ORDER},
    )
    figure.update_traces(textposition="outside")
    figure.update_layout(
        title="등급별 실제 이탈률",
        xaxis_title="",
        yaxis_title="실제 이탈률",
        yaxis_tickformat=".0%",
        yaxis_range=[0, max(0.62, float(data["observed_churn_rate"].max()) * 1.18)],
        showlegend=False,
    )
    return polish(figure)


def score_histogram(frame: pd.DataFrame) -> go.Figure:
    figure = px.histogram(
        frame,
        x="risk_score",
        color="risk_tier",
        color_discrete_map=TIER_COLORS,
        category_orders={"risk_tier": TIER_ORDER},
        nbins=34,
        opacity=0.88,
    )
    figure.update_layout(
        title="위험 점수 분포",
        xaxis_title="위험 점수 · 확률 아님",
        yaxis_title="리뷰어 수",
        bargap=0.04,
    )
    return polish(figure)


def top_k_curve(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["target_rate_pct"],
            y=frame["precision_at_k"] * 100,
            name="Precision@K",
            mode="lines+markers",
            line=dict(color=COLORS["focus"], width=3),
            marker=dict(size=8),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=frame["target_rate_pct"],
            y=frame["recall_at_k"] * 100,
            name="Recall@K",
            mode="lines+markers",
            line=dict(color=COLORS["primary"], width=3),
            marker=dict(size=8),
        )
    )
    figure.add_vline(
        x=20,
        line_dash="dash",
        line_color=COLORS["ink"],
        annotation_text="대표 정책 20%",
        annotation_position="top right",
    )
    figure.update_layout(
        title="CRM 처리 용량에 따른 포착 성능",
        xaxis_title="관리 대상 비율",
        yaxis_title="성능",
        yaxis_ticksuffix="%",
        yaxis_range=[0, 90],
    )
    return polish(figure)


def profile_activity(row: pd.Series) -> go.Figure:
    labels = ["리뷰 수", "활동 월", "고유 음식점"]
    baseline = [
        row.get("baseline_review_count", 0),
        row.get("baseline_active_months", 0),
        row.get("baseline_unique_business_count", 0),
    ]
    recent = [
        row.get("recent_review_count", 0),
        row.get("recent_active_months", 0),
        row.get("recent_unique_business_count", 0),
    ]
    figure = go.Figure(
        [
            go.Bar(
                name="선정 기간",
                x=labels,
                y=baseline,
                marker_color="#AEB9BF",
                text=baseline,
                textposition="outside",
            ),
            go.Bar(
                name="최근 관찰 기간",
                x=labels,
                y=recent,
                marker_color=COLORS["critical"],
                text=recent,
                textposition="outside",
            ),
        ]
    )
    figure.update_layout(
        title="선정 기간 대비 최근 활동",
        barmode="group",
        yaxis_title="건수 / 활동 월",
    )
    return polish(figure, 420)


def interval_comparison(row: pd.Series) -> go.Figure:
    data = pd.DataFrame(
        {
            "지표": ["평균 작성 간격", "마지막 리뷰 공백"],
            "선정 기간": [
                row.get("baseline_mean_interval_days", 0),
                row.get("baseline_recency_days", 0),
            ],
            "최근 관찰 기간": [
                row.get("recent_mean_interval_days", 0),
                row.get("recent_recency_days", 0),
            ],
        }
    ).melt(id_vars="지표", var_name="기간", value_name="일수")
    figure = px.bar(
        data,
        x="지표",
        y="일수",
        color="기간",
        barmode="group",
        text="일수",
        color_discrete_map={
            "선정 기간": "#AEB9BF",
            "최근 관찰 기간": COLORS["primary"],
        },
    )
    figure.update_traces(texttemplate="%{text:.0f}일", textposition="outside")
    figure.update_layout(
        title="작성 주기 변화",
        xaxis_title="",
        yaxis_title="일수",
    )
    return polish(figure, 420)


def monthly_activity(frame: pd.DataFrame) -> go.Figure:
    data = frame.copy()
    date_column = "year_month" if "year_month" in data.columns else "month"
    data[date_column] = pd.to_datetime(data[date_column].astype(str), errors="coerce")
    figure = px.line(
        data.sort_values(date_column),
        x=date_column,
        y="review_count",
        markers=True,
    )
    figure.update_traces(
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=7),
    )
    figure.update_layout(
        title="월별 리뷰 활동",
        xaxis_title="",
        yaxis_title="리뷰 수",
    )
    return polish(figure, 420)


def model_comparison(frame: pd.DataFrame) -> go.Figure:
    metrics = ["precision", "recall", "f1", "roc_auc", "pr_auc"]
    available = [column for column in metrics if column in frame.columns]
    long = frame.melt(
        id_vars=["dataset"],
        value_vars=available,
        var_name="metric",
        value_name="score",
    )
    figure = px.bar(
        long,
        x="metric",
        y="score",
        color="dataset",
        barmode="group",
        text=long["score"].map(lambda value: f"{value:.3f}"),
        color_discrete_map={
            "Validation": COLORS["watch"],
            "Test": COLORS["primary"],
        },
    )
    figure.update_traces(textposition="outside")
    figure.update_layout(
        title="Validation과 Test 성능 비교",
        xaxis_title="",
        yaxis_title="Score",
        yaxis_range=[0, 1],
    )
    return polish(figure, 430)


def feature_importance(frame: pd.DataFrame, top_n: int = 12) -> go.Figure:
    data = frame.nlargest(top_n, "importance_mean").sort_values("importance_mean")
    figure = px.bar(
        data,
        x="importance_mean",
        y="feature",
        orientation="h",
        color="feature_group",
        error_x="importance_std" if "importance_std" in data.columns else None,
        color_discrete_map=GROUP_COLORS,
        hover_data={
            "importance_share_pct": ":.1f"
        }
        if "importance_share_pct" in data.columns
        else None,
    )
    figure.update_layout(
        title="최종 모델 핵심 피처",
        xaxis_title="Permutation importance · PR-AUC 감소량",
        yaxis_title="",
    )
    return polish(figure, 480)


def group_importance(frame: pd.DataFrame) -> go.Figure:
    labels = {
        "activity": "리뷰 활동량",
        "interval": "작성 간격",
        "business": "음식점 탐색",
    }
    data = frame.copy()
    data["그룹"] = data["feature_group"].map(labels).fillna(data["feature_group"])
    data = data.sort_values("importance_mean")
    figure = px.bar(
        data,
        x="importance_mean",
        y="그룹",
        orientation="h",
        color="feature_group",
        text=data["importance_mean"].map(lambda value: f"{value:.3f}"),
        color_discrete_map=GROUP_COLORS,
    )
    figure.update_layout(
        title="그룹 제거 시 PR-AUC 감소",
        xaxis_title="PR-AUC 감소량",
        yaxis_title="",
        showlegend=False,
    )
    return polish(figure, 350)
