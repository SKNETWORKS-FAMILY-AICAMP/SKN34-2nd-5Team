from __future__ import annotations

import html

import streamlit as st

from core.components import (
    capability_grid,
    empty_state,
    footer,
    page_intro,
    render_warnings,
    section_header,
    signal_bars,
)
from core.data import load_app_data
from core.decisions import UNDECIDED_LABEL, with_manager_decisions
from core.insights import DECISION_PLAYBOOKS, DECISION_STATE_MAP


JUDGMENT_TO_DECISION = {
    "유지 우세": DECISION_STATE_MAP[0],
    "약화 우세": DECISION_STATE_MAP[1],
    "중단 우세": DECISION_STATE_MAP[2],
}

data = load_app_data()
profiles = with_manager_decisions(data.reviewer_profiles)
decision_counts = profiles["manager_decision"].value_counts()

page_intro(
    "Retention playbook",
    "운영 판단에 맞는 다음 행동을 정합니다",
    "관리자 판단을 고르면 위험 유형별 세부 전략과 실행 조건이 하나로 연결됩니다.",
    ["규칙 기반 프로토타입", "외부 연동 필요"],
)

view_mode = st.segmented_control(
    "화면 모드",
    ["전략 라이브러리", "현재 리뷰어에게 추천"],
    default="전략 라이브러리",
    key="playbook_view_mode",
    label_visibility="collapsed",
)

if view_mode == "현재 리뷰어에게 추천":
    empty_state(
        "현재 리뷰어 기준 추천",
        "Reviewer 360에서 특정 리뷰어의 판단 결과와 함께 들어와야 활성화됩니다.",
        "고도화 예정",
        [
            (
                "활성화 조건",
                "Reviewer 360 → 플레이북 이동 시 관리자 판단·위험 유형·모델 판단 전달 배선 필요",
            ),
        ],
    )
    render_warnings(data.warnings)
    footer(data.data_mode)
    st.stop()

decision_options = list(DECISION_PLAYBOOKS.keys()) + [UNDECIDED_LABEL]
selected_decision = st.segmented_control(
    "관리자 판단",
    decision_options,
    default=decision_options[0],
    key="playbook_decision_filter",
    label_visibility="collapsed",
)
if selected_decision is None:
    selected_decision = decision_options[0]

selected_model_judgment = None
if selected_decision == UNDECIDED_LABEL:
    st.html(
        """
        <div class="rr-playbook-model-hint">
          미검토는 아직 확정된 조치가 없어, 모델 판단으로 좁혀서 봅니다.
        </div>
        """
    )
    selected_model_judgment = st.segmented_control(
        "모델 판단",
        ["유지 우세", "약화 우세", "중단 우세"],
        default="중단 우세",
        key="playbook_model_judgment_filter",
        label_visibility="collapsed",
    )
    if selected_model_judgment is None:
        selected_model_judgment = "중단 우세"
    effective_decision = JUDGMENT_TO_DECISION[selected_model_judgment]
    is_confirmed = False
else:
    effective_decision = selected_decision
    is_confirmed = True

risk_type_options = ["전체"] + profiles["risk_type"].value_counts().index.tolist()
selected_risk_type = st.segmented_control(
    "위험 유형",
    risk_type_options,
    default="전체",
    key="playbook_risk_type",
    label_visibility="collapsed",
)
if selected_risk_type is None:
    selected_risk_type = "전체"

pool = profiles.loc[profiles["manager_decision"].eq(selected_decision)]
if selected_model_judgment:
    pool = pool.loc[pool["model_judgment"].eq(selected_model_judgment)]
if selected_risk_type != "전체":
    pool = pool.loc[pool["risk_type"].eq(selected_risk_type)]

playbook_entry = DECISION_PLAYBOOKS[effective_decision]
sub_strategy_text = playbook_entry["sub_strategy"].get(selected_risk_type)

status_label = "모델 추천 · 판단 전" if not is_confirmed else "규칙 기반 프로토타입"
sub_title = (
    f"{selected_decision} · {selected_model_judgment} 조합에 대한 추천 전략입니다."
    if not is_confirmed
    else f"실제로 이렇게 판단된 {len(pool):,}명에게 적용되는 전략입니다."
)

section_header(effective_decision, sub_title, status_label)

tiles_html = (
    '<div class="rr-playbook-grid">'
    '<div class="rr-playbook-tile">'
    '<div class="rr-playbook-tile-label">적용 검토 조건</div>'
    f'<div class="rr-playbook-tile-value">{html.escape(playbook_entry["condition"])}</div>'
    "</div>"
    '<div class="rr-playbook-tile">'
    '<div class="rr-playbook-tile-label">1차 운영 행동</div>'
    f'<div class="rr-playbook-tile-value">{html.escape(playbook_entry["primary_action"])}</div>'
    "</div>"
    "</div>"
)

if selected_risk_type != "전체":
    if sub_strategy_text:
        sub_html = (
            '<div class="rr-playbook-substrategy">'
            f'<div class="rr-playbook-substrategy-label">'
            f'세부 전략 · {html.escape(selected_risk_type)}</div>'
            f'<div class="rr-playbook-substrategy-value">{html.escape(sub_strategy_text)}</div>'
            "</div>"
        )
    else:
        sub_html = (
            '<div class="rr-playbook-substrategy rr-playbook-substrategy--empty">'
            f'<div class="rr-playbook-substrategy-label">세부 전략 · {html.escape(selected_risk_type)}</div>'
            '<div class="rr-playbook-substrategy-value">이 조합에 대한 세부 전략은 아직 정의되지 않았습니다.</div>'
            "</div>"
        )
else:
    sub_html = ""

bottom_html = (
    '<div class="rr-playbook-grid">'
    '<div>'
    '<div class="rr-playbook-tile-label">권장 채널</div>'
    f'<div class="rr-playbook-tile-value">{html.escape(playbook_entry["channel"])}</div>'
    "</div>"
    '<div>'
    '<div class="rr-playbook-tile-label">고도화 필요</div>'
    f'<div class="rr-playbook-tile-value" style="color:var(--rr-muted)">{html.escape(playbook_entry["needs_upgrade"])}</div>'
    "</div>"
    "</div>"
)

st.html(
    f'<div class="rr-playbook-card">{tiles_html}{sub_html}{bottom_html}</div>'
)

st.html(
    """
    <div class="rr-playbook-warn">
      <span>현재 플레이북은 행동 신호와 운영 아이디어를 연결한 규칙 기반 추천입니다.
      개입 효과가 검증된 처방이 아니며, 의학적 상태를 의미하지 않습니다.</span>
    </div>
    """
)

example_view = pool.nsmallest(10, "priority_rank")[
    [
        "priority_rank",
        "user_id",
        "risk_type",
        "model_judgment",
        "recent_active_months",
        "recent_recency_days",
    ]
].rename(
    columns={
        "priority_rank": "순위",
        "user_id": "리뷰어",
        "risk_type": "위험 유형",
        "model_judgment": "모델 판단",
        "recent_active_months": "최근 활동 월",
        "recent_recency_days": "최근 리뷰 공백",
    }
)
target_column, mix_column = st.columns([1.45, 0.55], gap="large")
with target_column:
    section_header(
        "이 판단에 해당하는 리뷰어",
        "참고용 목록입니다 · 처리는 리뷰어 관리에서 진행합니다.",
        "현재 사용 가능",
    )
    st.dataframe(
        example_view,
        hide_index=True,
        width="stretch",
        column_config={
            "순위": st.column_config.NumberColumn(format="%d위"),
            "최근 활동 월": st.column_config.NumberColumn(format="%.0f개월"),
            "최근 리뷰 공백": st.column_config.NumberColumn(format="%.0f일"),
        },
    )
with mix_column:
    section_header("판단별 규모", "현재 관리자 판단 분포")
    signal_bars([(str(label), int(value)) for label, value in decision_counts.items()])

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
