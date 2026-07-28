from __future__ import annotations

import streamlit as st

from core.components import (
    capability_grid,
    decision_band,
    empty_state,
    footer,
    metric_strip,
    page_intro,
    render_warnings,
    section_header,
)
from core.data import load_app_data


data = load_app_data()
region = data.regional_risk.copy()

page_intro(
    "Regional content risk",
    "콘텐츠 공급 위험을 지역 단위로 준비합니다",
    "거주지가 아닌 음식점 리뷰 활동 지역을 기준으로 정의와 데이터 준비 상태를 관리합니다.",
    ["현재 사용 가능" if not region.empty else "정의·데이터 필요"],
)
regional_source = data.sources.get(
    "regional_risk",
    "reports/tables/regional_risk_summary_v01.csv · 현재 미연결",
)
st.caption(
    "이 화면은 v04 모델 결과가 아닙니다. 지역 콘텐츠 위험 v01 데이터 계약을 "
    f"유지합니다. 출처 · {regional_source}"
)

if region.empty:
    section_header(
        "지역별 위험 우선순위",
        "데이터 연결 후 동일 화면에서 지역별 콘텐츠 공급 위험을 확인합니다.",
        "정의·데이터 필요",
    )
    map_column, activation_column = st.columns([1.2, 0.8], gap="large")
    with map_column:
        empty_state(
            "지역별 위험 집계 연결 대기",
            "지도나 순위표에 임의 수치를 넣지 않습니다. 리뷰 활동 음식점 기준의 지역 집계가 준비되면 활성화됩니다.",
            "데이터 연결 필요",
            [
                ("활동 리뷰어", "지역별 활동 리뷰어 수"),
                ("고위험 리뷰어", "긴급·집중 관리 리뷰어 수"),
                ("고위험 비율", "고위험 리뷰어 비율(0~1)"),
                ("리뷰 공급 변화", "최근 리뷰 생산량 변화 · 선택"),
            ],
        )
    with activation_column:
        section_header("해석 원칙", "분석 범위를 명확히 제한합니다.")
        st.info(
            "거주지, 직장, 실제 생활 반경을 추론하지 않습니다.",
            icon=":material/privacy_tip:",
        )
    section_header("활성화 순서", "가짜 지역 수치를 만들지 않는 조건")
    decision_band(
        [
            ("지역 정의", "음식점 활동 권역", "city/state 또는 권역"),
            ("표본 기준", "최소 리뷰어 수", "비율 왜곡 방지"),
            ("데이터 연결", "지역 집계 파일", "계약 검증 후 활성화"),
        ]
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
    metric_specs = [
        ("활동 리뷰어", "reviewers", "명"),
        ("고위험 리뷰어", "high_risk_users", "명"),
        ("고위험 비율", "high_risk_rate", "%"),
        ("리뷰 공급 변화", "review_supply_change", "%"),
    ]
    metric_items = []
    for label, field, suffix in metric_specs:
        if field not in selected or selected[field] is None:
            value = "—"
        elif suffix == "%":
            value = f"{float(selected[field]):.1%}"
        else:
            value = f"{int(selected[field]):,}{suffix}"
        metric_items.append((label, value, selected_region))
    metric_strip(metric_items)
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
items = [
    ("지역 우선순위", "위험 리뷰어 규모와 비율을 함께 비교", "정의·데이터 필요"),
    ("신규 리뷰어 유입", "지역별 콘텐츠 생산 기반 관찰", "데이터 연결 필요"),
    ("리뷰 공급 변화", "음식점 리뷰 감소 지역 탐지", "데이터 연결 필요"),
    ("탐방 미션 후보", "운영 검토 후 지역 미션 설계", "규칙 기반 프로토타입"),
]
capability_grid(items)

render_warnings(data.warnings)
footer(data.data_mode)
