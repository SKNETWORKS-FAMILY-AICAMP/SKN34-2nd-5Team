from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from core.charts import (
    feature_importance,
    group_importance,
    model_comparison,
    top_k_curve,
)
from core.components import (
    empty_state,
    footer,
    page_intro,
    render_warnings,
    section_header,
    status_badge,
)
from core.data import load_app_data


data = load_app_data()

page_intro(
    "Model trust & product readiness",
    "성능뿐 아니라 해석 범위와 제품 준비도를 공개합니다",
    "시간 분할, Top-K 성능, 피처 근거, 제한 사항과 확장 조건을 한곳에서 확인합니다.",
    ["현재 데모에서 사용 가능" if data.data_mode == "demo" else "현재 사용 가능"],
)
render_warnings(data.warnings)

view = st.segmented_control(
    "신뢰 센터 보기",
    ["성능과 Top-K", "시간 분할·누수 방지", "피처 근거", "제품 상태·로드맵"],
    default="성능과 Top-K",
    key="trust_view",
    width="stretch",
)

if view == "성능과 Top-K":
    validation_test = data.validation_test
    if validation_test.empty:
        empty_state(
            "Validation/Test 성능",
            "검증과 테스트 성능 파일이 연결되면 일반화 성능을 비교합니다.",
            "데이터 연결 필요",
        )
    else:
        section_header(
            "Validation과 Test",
            "검증 시점과 최종 Test 시점의 성능을 분리해서 확인합니다.",
            "현재 사용 가능",
        )
        validation = validation_test.loc[
            validation_test["dataset"].astype(str).str.lower().eq("validation")
        ]
        test = validation_test.loc[
            validation_test["dataset"].astype(str).str.lower().eq("test")
        ]
        metric_source = test.iloc[0] if not test.empty else validation_test.iloc[-1]
        metrics = st.columns(4, gap="large")
        metric_specs = [
            ("PR-AUC", "pr_auc", "불균형 데이터 핵심 지표"),
            ("ROC-AUC", "roc_auc", "전체 순위 구분 성능"),
            ("Recall", "recall", "전체 이탈자 포착률"),
            ("Precision", "precision", "선별 대상 내 실제 이탈"),
        ]
        for column, (label, field, note) in zip(metrics, metric_specs):
            with column:
                value = float(metric_source.get(field, 0.0))
                st.metric(label, f"{value:.3f}" if "AUC" in label else f"{value:.1%}")
                st.caption(f"Test · {note}")
        st.plotly_chart(
            model_comparison(validation_test),
            width="stretch",
            key="trust_model_comparison",
        )

    section_header(
        "Top-K 운영 효율",
        "검토 가능한 인원 비율에 따라 포착 성능과 Lift가 어떻게 달라지는지 보여줍니다.",
        "현재 사용 가능",
    )
    if data.top_k.empty:
        empty_state(
            "Top-K 성능",
            "Top-K 결과 파일이 연결되면 정책별 Recall과 Lift를 표시합니다.",
            "데이터 연결 필요",
        )
    else:
        st.plotly_chart(
            top_k_curve(data.top_k),
            width="stretch",
            key="trust_top_k_curve",
        )
        top_k_table = data.top_k.copy().rename(
            columns={
                "target_rate_pct": "검토 비율",
                "target_users": "검토 인원",
                "captured_churn_users": "포착 이탈자",
                "precision_at_k": "Precision@K",
                "recall_at_k": "Recall@K",
                "lift_at_k": "Lift@K",
                "minimum_risk_score": "최소 점수",
            }
        )
        st.dataframe(
            top_k_table,
            hide_index=True,
            width="stretch",
            column_config={
                "검토 비율": st.column_config.NumberColumn(format="%d%%"),
                "Precision@K": st.column_config.NumberColumn(format="%.1%%"),
                "Recall@K": st.column_config.NumberColumn(format="%.1%%"),
                "Lift@K": st.column_config.NumberColumn(format="%.2f×"),
                "최소 점수": st.column_config.NumberColumn(format="%.4f"),
            },
        )

elif view == "시간 분할·누수 방지":
    section_header(
        "시간 순서를 지키는 평가 구조",
        "운영 시점에 알 수 없는 미래 정보를 피처에 포함하지 않습니다.",
        "현재 사용 가능",
    )
    timeline = st.columns(3, gap="large")
    timeline_specs = [
        ("선정 기준", "2017", "분석 대상 정의"),
        ("관찰 기간", "2018", "행동 피처 생성"),
        ("검증 기간", "2019", "실제 결과 확인"),
    ]
    for column, (label, value, copy) in zip(timeline, timeline_specs):
        with column:
            st.metric(label, value)
            st.caption(copy)

    if not data.split_summary.empty:
        st.dataframe(data.split_summary, hide_index=True, width="stretch")

    section_header("누수 방지와 해석 원칙")
    st.markdown(
        """
        - 미래 연도의 리뷰 활동은 예측 피처에서 제외합니다.
        - 실제 이탈 결과는 Reviewer 360의 기본 화면에서 숨깁니다.
        - 위험 점수는 보정된 이탈 확률이 아니라 상대적 위험 순위용 모델 점수입니다.
        - 거주지나 직장, 실제 생활 변화를 리뷰 데이터로 추론하지 않습니다.
        - `Useful`, `Cool`, `Funny`는 시간 누수 위험 때문에 현재 모델에서 제외합니다.
        """
    )

elif view == "피처 근거":
    feature_column, group_column = st.columns([1.2, 0.8], gap="large")
    with feature_column:
        section_header(
            "피처 중요도",
            "최종 모델 전체의 주요 판단 근거입니다.",
            "현재 사용 가능" if not data.feature_importance.empty else "데이터 연결 필요",
        )
        if data.feature_importance.empty:
            empty_state(
                "피처 중요도",
                "검증된 중요도 결과 파일을 연결해야 표시할 수 있습니다.",
                "데이터 연결 필요",
            )
        else:
            st.plotly_chart(
                feature_importance(data.feature_importance),
                width="stretch",
                key="trust_feature_importance",
            )
    with group_column:
        section_header(
            "피처 그룹",
            "활동량·작성 간격·탐색 다양성의 기여를 비교합니다.",
            "현재 사용 가능" if not data.group_importance.empty else "데이터 연결 필요",
        )
        if data.group_importance.empty:
            empty_state(
                "피처 그룹 중요도",
                "그룹 중요도 결과 파일을 연결해야 표시할 수 있습니다.",
                "데이터 연결 필요",
            )
        else:
            st.plotly_chart(
                group_importance(data.group_importance),
                width="stretch",
                key="trust_group_importance",
            )

    section_header(
        "개인별 설명 범위",
        "현재 운영 화면과 향후 분석 기능을 구분합니다.",
    )
    scope = pd.DataFrame(
        [
            ["행동 변화 비교", "현재 사용 가능", "프로필 집계 컬럼"],
            ["규칙 기반 위험 근거", "규칙 기반 프로토타입", "설명 규칙 검증 필요"],
            ["개인별 SHAP", "분석 검증 필요", "설명 안정성 검증 필요"],
            ["보정된 이탈 확률", "현재 제외", "Calibration 필요"],
        ],
        columns=["설명 기능", "상태", "조건"],
    )
    st.dataframe(scope, hide_index=True, width="stretch")

else:
    section_header(
        "제품 상태와 확장 조건",
        "기능별 현재 상태, 필요한 데이터와 활성화 후 가치를 공개합니다.",
    )
    roadmap = [
        (
            "운영 홈·검토 큐",
            "현재 사용 가능",
            "위험 프로필 결과",
            "우선 검토 대상 발견",
        ),
        (
            "위험 유형 플레이북",
            "규칙 기반 프로토타입",
            "규칙 검증·운영 피드백",
            "일관된 개입 판단",
        ),
        (
            "월별 활동 타임라인",
            "데이터 연결 필요",
            "월별 리뷰 활동 파일",
            "감소 시점·회복 확인",
        ),
        (
            "지역 콘텐츠 위험",
            "정의·데이터 필요",
            "지역 정의·최소 표본·집계",
            "지역별 콘텐츠 공급 대응",
        ),
        (
            "캠페인 성과 추적",
            "외부 연동 필요",
            "CRM 발송·참여·복귀 데이터",
            "개입 효과 비교",
        ),
        (
            "개인별 SHAP·보정 확률",
            "분석 검증 필요",
            "설명 안정성·Calibration",
            "세부 근거·확률 해석",
        ),
    ]
    markup = (
        '<div class="rr-roadmap rr-roadmap--head">'
        "<span>기능</span><span>현재 상태</span>"
        "<span>필요 데이터·검증</span><span>활성화 후 제공 가치</span></div>"
    )
    for feature, status, need, value in roadmap:
        markup += (
            '<div class="rr-roadmap">'
            f"<strong>{html.escape(feature)}</strong>"
            f"<span>{status_badge(status)}</span>"
            f"<span>{html.escape(need)}</span>"
            f"<span>{html.escape(value)}</span></div>"
        )
    st.html(markup)

    section_header(
        "연결된 산출물",
        "현재 앱이 실제로 읽고 있는 데이터 파일입니다.",
    )
    if data.sources:
        sources = pd.DataFrame(
            [{"데이터": key, "출처": value} for key, value in data.sources.items()]
        )
        st.dataframe(sources, hide_index=True, width="stretch")
    else:
        st.caption("연결된 프로젝트 산출물이 없습니다.")

footer(data.data_mode)
