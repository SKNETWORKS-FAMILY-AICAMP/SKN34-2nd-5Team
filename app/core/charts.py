from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.theme import COLORS


GROUP_COLORS = {
    "activity": COLORS["primary"],
    "interval": COLORS["watch"],
    "business": COLORS["focus"],
}
STATE_ORDER = ["파워 지위 유지", "파워 지위 약화", "리뷰 활동 중단"]
STATE_COLORS = {
    "파워 지위 유지": COLORS["primary"],
    "파워 지위 약화": "#D48A43",
    "리뷰 활동 중단": COLORS["critical"],
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


def retention_state_distribution(frame: pd.DataFrame) -> go.Figure:
    data = frame.copy()
    figure = px.bar(
        data,
        x="predicted_state_label",
        y="users",
        color="predicted_state_label",
        text="users",
        color_discrete_map=STATE_COLORS,
        category_orders={"predicted_state_label": STATE_ORDER},
    )
    figure.update_traces(
        texttemplate="%{text:,.0f}명",
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,.0f}명<extra></extra>",
    )
    figure.update_layout(
        title="모델 판단 분포",
        xaxis_title="",
        yaxis_title="리뷰어 수",
        showlegend=False,
    )
    return polish(figure, 320)


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
        barmode="group",
        yaxis_title="",
        legend_orientation="h",
        legend_y=1.08,
    )
    return polish(figure, 285)


def interval_comparison(row: pd.Series) -> go.Figure:
    def finite(value: object) -> float | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if math.isfinite(numeric) else None

    rows: list[dict[str, object]] = []
    metrics = [
        (
            "평균 작성 간격",
            finite(row.get("baseline_mean_interval_days")),
            finite(row.get("recent_mean_interval_days")),
        ),
        (
            "마지막 리뷰 공백",
            finite(row.get("baseline_recency_days")),
            finite(row.get("recent_recency_days")),
        ),
    ]
    unavailable_interval = False
    for label, baseline, recent in metrics:
        if baseline is None or recent is None:
            unavailable_interval = unavailable_interval or label == "평균 작성 간격"
            continue
        rows.extend(
            [
                {"지표": label, "기간": "선정 기간", "일수": baseline},
                {"지표": label, "기간": "최근 관찰 기간", "일수": recent},
            ]
        )
    data = pd.DataFrame(rows)
    if data.empty:
        figure = go.Figure()
        figure.add_annotation(
            text="작성 간격을 계산할 수 있는 리뷰가 없습니다.",
            showarrow=False,
            font=dict(color=COLORS["muted"], size=12),
        )
        return polish(figure, 285)
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
        xaxis_title="",
        yaxis_title="",
        legend_orientation="h",
        legend_y=1.08,
    )
    if unavailable_interval:
        figure.add_annotation(
            text="최근 기간 리뷰가 1건이라 평균 작성 간격은 표시하지 않습니다.",
            xref="paper",
            yref="paper",
            x=0,
            y=1.14,
            xanchor="left",
            showarrow=False,
            font=dict(color=COLORS["muted"], size=10),
        )
    return polish(figure, 285)


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


CLASS_STATE_ORDER = ["유지", "약화", "중단"]
CLASS_STATE_MAP = {"retained": "유지", "weakened": "약화", "stopped": "중단"}
METRIC_COLORS = {
    "Precision": COLORS["primary"],
    "Recall": COLORS["focus"],
    "F1": COLORS["watch"],
    "PR-AUC": COLORS["critical"],
}


def multiclass_class_performance(frame: pd.DataFrame) -> go.Figure:
    row = frame.loc[frame["record_type"].eq("final_test")].iloc[0]
    metric_specs = [
        ("precision", "Precision"),
        ("recall", "Recall"),
        ("f1", "F1"),
        ("pr_auc", "PR-AUC"),
    ]
    rows = [
        {"클래스": label_ko, "지표": metric_label, "값": float(row[f"{code}_{metric}"])}
        for code, label_ko in CLASS_STATE_MAP.items()
        for metric, metric_label in metric_specs
    ]
    data = pd.DataFrame(rows)
    figure = px.bar(
        data,
        x="클래스",
        y="값",
        color="지표",
        barmode="group",
        text=data["값"].map(lambda value: f"{value:.3f}"),
        category_orders={"클래스": CLASS_STATE_ORDER},
        color_discrete_map=METRIC_COLORS,
    )
    figure.update_traces(textposition="outside")
    figure.update_layout(
        title="클래스별 Test 성능",
        xaxis_title="",
        yaxis_title="Score",
        yaxis_range=[0, 1],
    )
    return polish(figure, 400)


def multiclass_top_k_curve(frame: pd.DataFrame) -> go.Figure:
    data = frame.loc[
        frame["split"].eq("final_test") & frame["ranking"].eq("unified")
    ].sort_values("target_rate")
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["target_rate"] * 100,
            y=data["status_loss_precision"] * 100,
            name="Precision",
            mode="lines+markers",
            line=dict(color=COLORS["focus"], width=3),
            marker=dict(size=8),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["target_rate"] * 100,
            y=data["status_loss_recall"] * 100,
            name="Recall",
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
        title="통합 우선순위 Top-K 성과 · 지위 상실 기준",
        xaxis_title="검토 대상 비율",
        yaxis_title="성능",
        yaxis_ticksuffix="%",
        yaxis_range=[0, 100],
    )
    return polish(figure)


def confusion_heatmap(frame: pd.DataFrame) -> go.Figure:
    subset = frame.loc[
        frame["split"].eq("final_test") & frame["decision_policy"].eq("threshold")
    ]
    order = ["retained", "weakened", "stopped"]
    pivot = (
        subset.pivot(index="actual_state", columns="predicted_state", values="users")
        .reindex(index=order, columns=order)
    )
    labels = [CLASS_STATE_MAP[code] for code in order]
    figure = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=labels,
            y=labels,
            text=pivot.values,
            texttemplate="%{text:,}명",
            colorscale=[[0, "#F1F4F1"], [1, COLORS["primary"]]],
            showscale=False,
            hovertemplate="실제 %{y} · 판단 %{x}<br>%{z:,}명<extra></extra>",
        )
    )
    figure.update_layout(
        title="실제 상태 × 모델 판단 · Test",
        xaxis_title="모델 판단",
        yaxis_title="실제 상태",
        yaxis_autorange="reversed",
    )
    return polish(figure, 380)
