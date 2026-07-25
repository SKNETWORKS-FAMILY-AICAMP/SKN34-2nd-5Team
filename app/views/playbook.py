from __future__ import annotations

import pandas as pd
import streamlit as st

from core.components import (
    capability_grid,
    decision_band,
    empty_state,
    footer,
    page_intro,
    render_warnings,
    section_header,
    signal_bars,
)
from core.data import load_app_data
from core.insights import STRATEGIES


data = load_app_data()
profiles = data.reviewer_profiles
type_counts = profiles["risk_type"].value_counts()

page_intro(
    "Retention playbook",
    "위험 신호를 개입 전략으로 연결합니다",
    "유형을 선택하면 적용 조건, 1차 개입과 권장 채널이 하나의 실행 구조로 연결됩니다.",
    ["규칙 기반 프로토타입", "외부 연동 필요"],
)

selected_type = st.segmented_control(
    "위험 유형",
    options=type_counts.index.tolist(),
    default=type_counts.index[0],
    key="playbook_risk_type",
    width="stretch",
)
if selected_type is None:
    selected_type = type_counts.index[0]

selected_judgments = st.multiselect(
    "개입 방향 · 모델 판단",
    options=["약화 우세", "중단 우세", "유지 우세"],
    default=[],
    placeholder="전체",
    key="playbook_judgment_filter",
    help="약화 우세는 활동 회복, 중단 우세는 복귀·재활성화 플레이북을 우선 검토합니다.",
)

strategy = STRATEGIES[str(selected_type)]
count = int(type_counts.get(selected_type, 0))

condition_map = {
    "복합 위험형": "활동량·작성 간격·탐색 중 두 개 이상의 강한 약화 신호",
    "활동량 붕괴형": "리뷰 수 또는 활동 월 감소가 가장 강한 변화",
    "작성 주기 이완형": "마지막 리뷰 공백 또는 평균 작성 간격 증가",
    "탐색 활동 축소형": "고유 음식점 수 감소가 가장 강한 변화",
    "일반 모니터링형": "급격한 활동 붕괴 신호가 확인되지 않은 상태",
}

section_header(
    f"{selected_type} · {count:,}명",
    strategy["summary"],
    "규칙 기반 프로토타입",
)
decision_band(
    [
        ("적용 조건", condition_map[str(selected_type)], "관찰 신호"),
        ("1차 개입", strategy["primary"], "운영자 검토"),
        ("권장 채널", strategy["channel"], "실행 접점"),
    ]
)

st.warning(
    "현재 플레이북은 행동 신호와 운영 아이디어를 연결한 규칙 기반 추천입니다. "
    "개입 효과가 검증된 처방이 아니며, 의학적 상태를 의미하지 않습니다.",
    icon=":material/warning:",
)

examples_pool = profiles.loc[profiles["risk_type"].eq(selected_type)]
if selected_judgments:
    examples_pool = examples_pool.loc[examples_pool["model_judgment"].isin(selected_judgments)]
examples = examples_pool.nsmallest(10, "priority_rank").copy()
example_view = examples[
    [
        "priority_rank",
        "user_id",
        "model_judgment",
        "weakened_score",
        "stopped_score",
        "recent_active_months",
        "recent_recency_days",
        "recommended_action",
    ]
].rename(
    columns={
        "priority_rank": "순위",
        "user_id": "리뷰어",
        "model_judgment": "모델 판단",
        "weakened_score": "약화 점수",
        "stopped_score": "중단 점수",
        "recent_active_months": "최근 활동 월",
        "recent_recency_days": "최근 리뷰 공백",
        "recommended_action": "권장 행동",
    }
)
target_column, mix_column = st.columns([1.45, 0.55], gap="large")
with target_column:
    section_header(
        "우선 적용 후보",
        "선택한 유형에 해당하는 상위 리뷰어입니다.",
        "현재 사용 가능",
    )
    st.dataframe(
        example_view,
        hide_index=True,
        width="stretch",
        column_config={
            "순위": st.column_config.NumberColumn(format="%d위"),
            "약화 점수": st.column_config.NumberColumn(format="%.4f"),
            "중단 점수": st.column_config.NumberColumn(format="%.4f"),
            "최근 활동 월": st.column_config.NumberColumn(format="%.0f개월"),
            "최근 리뷰 공백": st.column_config.NumberColumn(format="%.0f일"),
        },
    )
with mix_column:
    section_header("유형별 규모", "현재 규칙 분류 결과")
    signal_bars([(str(label), int(value)) for label, value in type_counts.items()])

section_header(
    "캠페인 실행과 성과 추적",
    "제품 구조는 준비하되 CRM 연결 전에는 실행 기능을 활성화하지 않습니다.",
    "외부 연동 필요",
)
campaign_items = [
    ("대상 배정", "담당자·채널·예정일", "외부 연동 필요"),
    ("접촉 이력", "발송·열람·클릭", "외부 연동 필요"),
    ("복귀 관찰", "리뷰 재개 여부", "데이터 연결 필요"),
    ("성과 비교", "플레이북별 효과", "분석 검증 필요"),
]
capability_grid(campaign_items)

with st.container(horizontal=True, vertical_alignment="bottom"):
    st.text_input(
        "캠페인 담당자",
        value="CRM 연결 후 지정",
        disabled=True,
        key="playbook_campaign_owner",
        width="stretch",
    )
    st.selectbox(
        "실행 채널",
        ["CRM 연결 후 활성화"],
        disabled=True,
        key="playbook_campaign_channel",
        width=220,
    )
    st.button(
        "캠페인 생성",
        disabled=True,
        icon=":material/add_task:",
    )

empty_state(
    "개입 효과 실험 설계",
    "발송군·비발송군, 참여 여부, 복귀 여부를 연결하면 플레이북별 성과 비교가 활성화됩니다.",
    "외부 연동 필요",
    [
        ("필요 데이터", "캠페인 ID, 배정 일자, 채널, 참여, 복귀 결과"),
        ("활성화 조건", "CRM 이벤트 계약과 효과 측정 기준 확정"),
    ],
)

render_warnings(data.warnings)
footer(data.data_mode)
