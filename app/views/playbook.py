from __future__ import annotations

import pandas as pd
import streamlit as st

from core.components import (
    empty_state,
    footer,
    page_intro,
    render_warnings,
    section_header,
)
from core.data import load_app_data
from core.insights import STRATEGIES


data = load_app_data()
profiles = data.reviewer_profiles
type_counts = profiles["risk_type"].value_counts()

page_intro(
    "Retention playbook",
    "관찰된 변화 신호를 운영 행동으로 연결합니다",
    "위험 유형별 적용 조건과 권장 행동을 보여주고, 아직 검증되지 않았거나 외부 연동이 필요한 기능을 구분합니다.",
    ["규칙 기반 프로토타입", "외부 연동 필요"],
)
render_warnings(data.warnings)

selected_type = st.segmented_control(
    "위험 유형",
    options=type_counts.index.tolist(),
    default=type_counts.index[0],
    key="playbook_risk_type",
    width="stretch",
)
if selected_type is None:
    selected_type = type_counts.index[0]

strategy = STRATEGIES[str(selected_type)]
count = int(type_counts.get(selected_type, 0))

headline, population = st.columns([1.5, 0.5], gap="large")
with headline:
    st.subheader(str(selected_type))
    st.write(strategy["summary"])
with population:
    st.metric("현재 분류 리뷰어", f"{count:,}명")
    st.caption("규칙 기반 분류 결과")

condition_map = {
    "복합 위험형": "활동량·작성 간격·탐색 중 두 개 이상의 강한 약화 신호",
    "활동량 붕괴형": "리뷰 수 또는 활동 월 감소가 가장 강한 변화",
    "작성 주기 이완형": "마지막 리뷰 공백 또는 평균 작성 간격 증가",
    "탐색 활동 축소형": "고유 음식점 수 감소가 가장 강한 변화",
    "일반 모니터링형": "급격한 활동 붕괴 신호가 확인되지 않은 상태",
}

section_header(
    "운영 판단 구조",
    "유형을 행동으로 연결하되, 최종 개입 강도는 운영자가 결정합니다.",
)
decision_columns = st.columns(3, gap="large")
with decision_columns[0]:
    st.markdown("#### 적용 조건")
    st.write(condition_map[str(selected_type)])
with decision_columns[1]:
    st.markdown("#### 1차 개입")
    st.write(strategy["primary"])
with decision_columns[2]:
    st.markdown("#### 권장 채널")
    st.write(strategy["channel"])

st.warning(
    "현재 플레이북은 행동 신호와 운영 아이디어를 연결한 규칙 기반 추천입니다. "
    "개입 효과가 검증된 처방이 아니며, 의학적 상태를 의미하지 않습니다.",
    icon=":material/warning:",
)

section_header(
    "해당 유형의 우선 검토 대상",
    "실제 프로필에서 선택한 위험 유형에 해당하는 상위 리뷰어입니다.",
    "현재 사용 가능",
)
examples = (
    profiles.loc[profiles["risk_type"].eq(selected_type)]
    .nsmallest(10, "risk_rank")
    .copy()
)
example_view = examples[
    [
        "risk_rank",
        "user_id",
        "risk_tier",
        "risk_score",
        "recent_active_months",
        "recent_recency_days",
        "recommended_action",
    ]
].rename(
    columns={
        "risk_rank": "순위",
        "user_id": "리뷰어",
        "risk_tier": "등급",
        "risk_score": "모델 점수",
        "recent_active_months": "최근 활동 월",
        "recent_recency_days": "최근 리뷰 공백",
        "recommended_action": "권장 행동",
    }
)
st.dataframe(
    example_view,
    hide_index=True,
    width="stretch",
    column_config={
        "순위": st.column_config.NumberColumn(format="%d위"),
        "모델 점수": st.column_config.NumberColumn(format="%.4f"),
        "최근 활동 월": st.column_config.NumberColumn(format="%.0f개월"),
        "최근 리뷰 공백": st.column_config.NumberColumn(format="%.0f일"),
    },
)

section_header(
    "캠페인 실행과 성과 추적",
    "제품 구조는 준비하되 CRM 연결 전에는 실행 기능을 활성화하지 않습니다.",
    "외부 연동 필요",
)
campaign_columns = st.columns(4, gap="large")
campaign_items = [
    ("대상 배정", "담당자·채널·예정일"),
    ("접촉 이력", "발송·열람·클릭"),
    ("복귀 관찰", "리뷰 재개 여부"),
    ("성과 비교", "플레이북별 효과"),
]
for column, (title, copy) in zip(campaign_columns, campaign_items):
    with column:
        st.markdown(f"#### {title}")
        st.caption(copy)

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

footer(data.data_mode)
