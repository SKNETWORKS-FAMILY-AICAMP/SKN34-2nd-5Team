from __future__ import annotations

import streamlit as st

from core.components import (
    empty_state,
    footer,
    page_intro,
    render_warnings,
    section_header,
)
from core.data import load_app_data


data = load_app_data()
region = data.regional_risk.copy()

page_intro(
    "Regional content risk",
    "위험 리뷰어가 집중된 리뷰 활동 지역을 찾습니다",
    "지역 기준과 최소 표본 기준이 확정되기 전에는 수치를 만들지 않습니다. 거주지가 아니라 리뷰가 작성된 음식점 기준의 활동 지역만 다룹니다.",
    ["현재 사용 가능" if not region.empty else "정의·데이터 필요"],
)
render_warnings(data.warnings)

if region.empty:
    section_header(
        "지역별 위험 우선순위",
        "데이터 연결 후 동일 화면에서 지역별 콘텐츠 공급 위험을 확인합니다.",
        "정의·데이터 필요",
    )
    map_column, activation_column = st.columns([1.15, 0.85], gap="large")
    with map_column:
        empty_state(
            "지역별 위험 집계 연결 대기",
            "지도나 순위표에 임의 수치를 넣지 않습니다. 리뷰 활동 음식점 기준의 지역 집계가 준비되면 활성화됩니다.",
            "데이터 연결 필요",
            [
                ("활동 리뷰어", "reviewers"),
                ("고위험 리뷰어", "high_risk_users"),
                ("고위험 비율", "high_risk_rate"),
                ("리뷰 공급 변화", "review_supply_change · 선택"),
            ],
        )
    with activation_column:
        st.markdown("#### 활성화 조건")
        st.markdown(
            """
            1. **지역 정의 확정**  
               city/state 또는 음식점 리뷰 활동 권역
            2. **최소 표본 기준 검증**  
               소수 리뷰어로 인한 비율 왜곡 방지
            3. **집계 파일 연결**  
               `regional_risk_summary_v01.csv`
            """
        )
        st.info(
            "거주지, 직장, 실제 생활 반경을 추론하지 않습니다.",
            icon=":material/privacy_tip:",
        )
else:
    region_name = next(
        (
            column
            for column in ["region_name", "region", "city", "state"]
            if column in region.columns
        ),
        region.columns[0],
    )
    selected_region = st.selectbox(
        "리뷰 활동 지역",
        options=region[region_name].dropna().astype(str).tolist(),
        key="selected_region",
        width=300,
    )
    selected = region.loc[region[region_name].astype(str).eq(selected_region)].iloc[0]
    metrics = st.columns(4, gap="large")
    metric_specs = [
        ("활동 리뷰어", "reviewers", "명"),
        ("고위험 리뷰어", "high_risk_users", "명"),
        ("고위험 비율", "high_risk_rate", "%"),
        ("리뷰 공급 변화", "review_supply_change", "%"),
    ]
    for column, (label, field, suffix) in zip(metrics, metric_specs):
        with column:
            if field not in selected or selected[field] is None:
                st.metric(label, "—")
            elif suffix == "%":
                st.metric(label, f"{float(selected[field]):.1%}")
            else:
                st.metric(label, f"{int(selected[field]):,}{suffix}")
    section_header(
        "지역 우선순위",
        "최소 표본 조건을 충족한 지역만 표시합니다.",
        "현재 사용 가능",
    )
    st.dataframe(region, hide_index=True, width="stretch")

section_header(
    "연결 후 운영 기능",
    "데이터가 준비되면 같은 화면에서 다음 판단을 지원합니다.",
)
capabilities = st.columns(4, gap="large")
items = [
    ("지역 우선순위", "위험 리뷰어 규모와 비율을 함께 비교"),
    ("신규 리뷰어 유입", "지역별 콘텐츠 생산 기반 관찰"),
    ("리뷰 공급 변화", "음식점 리뷰 감소 지역 탐지"),
    ("탐방 미션 후보", "운영 검토 후 지역 미션 설계"),
]
for column, (title, copy) in zip(capabilities, items):
    with column:
        st.markdown(f"#### {title}")
        st.caption(copy)

footer(data.data_mode)
