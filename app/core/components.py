from __future__ import annotations

import html
from collections.abc import Iterable
from urllib.parse import quote

import streamlit as st


STATUS_CLASS = {
    "현재 사용 가능": "now",
    "현재 데모에서 사용 가능": "now",
    "규칙 기반 프로토타입": "rule",
    "데이터 연결 필요": "data",
    "정의·데이터 필요": "definition",
    "분석 검증 필요": "analysis",
    "외부 연동 필요": "external",
    "고도화 예정": "external",
    "현재 제외": "excluded",
    "긴급 검토": "critical",
}

ICON_PATHS = {
    "rate_review": '<path d="M4 5.5h16v11H9l-5 3v-14Z"/><path d="m12 8 1 2 2.2.3-1.6 1.6.4 2.1-2-1-2 1 .4-2.1-1.6-1.6 2.2-.3 1-2Z"/>',
    "calendar_month": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4m8-4v4M4 10h16M8 14h2m3 0h3m-8 3h3"/>',
    "location_on": '<path d="M12 21s6-5.2 6-11a6 6 0 1 0-12 0c0 5.8 6 11 6 11Z"/><circle cx="12" cy="10" r="2.2"/>',
    "hourglass_empty": '<path d="M7 3h10M7 21h10M8 3c0 4 1.4 6.2 4 9-2.6 2.8-4 5-4 9m8-18c0 4-1.4 6.2-4 9 2.6 2.8 4 5 4 9"/>',
    "groups": '<circle cx="9" cy="9" r="3"/><circle cx="17" cy="10" r="2.3"/><path d="M3.5 20c.4-4 2.2-6 5.5-6s5.1 2 5.5 6m.5-5.2c3.2-.5 5 1.1 5.5 4.2"/>',
    "lock": '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
}


def svg_icon(name: str) -> str:
    paths = ICON_PATHS.get(name, ICON_PATHS["rate_review"])
    return (
        '<svg class="rr-svg-icon" viewBox="0 0 24 24" aria-hidden="true" '
        'fill="none" stroke="currentColor" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    )


def status_badge(status: str) -> str:
    class_name = STATUS_CLASS.get(status, "excluded")
    return (
        f'<span class="rr-badge rr-badge--{class_name}">'
        f"{html.escape(status)}</span>"
    )


def page_intro(
    eyebrow: str,
    title: str,
    description: str,
    statuses: Iterable[str] | None = None,
) -> None:
    badges = "".join(status_badge(status) for status in statuses or [])
    st.html(
        f"""
        <header class="rr-page-head">
          <div>
            <div class="rr-eyebrow">{html.escape(eyebrow)}</div>
            <div class="rr-title">{html.escape(title)}</div>
            <div class="rr-copy">{html.escape(description)}</div>
          </div>
          <div class="rr-badges">{badges}</div>
        </header>
        """
    )


def operations_brief(
    *,
    total_reviewers: int,
    urgent_users: int,
    crm_users: int,
    recall: float,
) -> None:
    st.html(
        f"""
        <section class="rr-brief">
          <div class="rr-brief-main">
            전체 {total_reviewers:,}명 중
            <strong>긴급 검토 {urgent_users:,}명</strong>입니다.<br>
            CRM 검토 대상 {crm_users:,}명부터 확인하세요.
          </div>
          <div class="rr-brief-note">
            <strong>운영 기준</strong><br>
            위험 점수 상위 20%를 CRM 검토 대상으로 정의합니다.
            이 정책은 전체 이탈자의 {recall:.1%}를 사전 포착했습니다.
            점수는 이탈 확률이 아닌 상대적 위험 순위입니다.
          </div>
        </section>
        """
    )


def policy_brief(
    *,
    crm_users: int,
    urgent_users: int,
    captured_users: int,
    recall: float,
) -> None:
    progress = max(0.0, min(100.0, recall * 100))
    st.html(
        f"""
        <section class="rr-policy-panel">
          <div class="rr-policy-top">
            <div>
              <div class="rr-eyebrow">Validated operating policy</div>
              <h2>상위 20%부터 검토합니다</h2>
              <p>위험 순위를 운영 용량에 맞춰 좁힌 현재 정책입니다.</p>
            </div>
            <div class="rr-radial" style="--progress:{progress:.2f}%">
              <div><strong>{progress:.1f}%</strong><span>Recall@20</span></div>
            </div>
          </div>
          <div class="rr-policy-lines">
            <div><i class="is-critical"></i><span>긴급 검토</span><strong>{urgent_users:,}명</strong></div>
            <div><i></i><span>CRM 검토 대상</span><strong>{crm_users:,}명</strong></div>
            <div><i></i><span>실제 이탈 포착</span><strong>{captured_users:,}명</strong></div>
          </div>
          <small>점수는 이탈 확률이 아닌 상대적 위험 순위입니다.</small>
        </section>
        """
    )


def validated_policy_brief(
    *,
    target_users: int,
    captured_users: int,
    precision: float,
    recall: float,
    lift: float,
    stopped_captured: int,
    stopped_recall: float,
    weakened_captured: int,
    weakened_recall: float,
) -> None:
    progress = max(0.0, min(100.0, precision * 100))
    st.html(
        f"""
        <section class="rr-policy-panel">
          <div class="rr-policy-top">
            <div>
              <div class="rr-eyebrow">Validated queue policy</div>
              <h2>통합 상위 20%부터 검토합니다</h2>
              <p>약화·중단 점수를 합산한 운영 우선순위입니다.</p>
            </div>
            <div class="rr-radial" style="--progress:{progress:.2f}%">
              <div><strong>{progress:.1f}%</strong><span>정밀도</span></div>
            </div>
          </div>
          <div class="rr-policy-lines">
            <div><i></i><span>통합 검토 대상</span><strong>{target_users:,}명</strong></div>
            <div><i class="is-critical"></i><span>실제 지위 상실 포착</span><strong>{captured_users:,}명</strong></div>
            <div><i></i><span>지위 상실 Recall</span><strong>{recall:.1%}</strong></div>
            <div><i></i><span>무작위 대비 Lift</span><strong>{lift:.2f}×</strong></div>
          </div>
          <div class="rr-policy-split">
            <span>중단 {stopped_captured:,}명 · Recall {stopped_recall:.1%}</span>
            <span>약화 {weakened_captured:,}명 · Recall {weakened_recall:.1%}</span>
          </div>
          <small>사후 Test 검증 결과이며 모델 점수는 상태 확률이 아닙니다.</small>
        </section>
        """
    )


def metric_strip(items: Iterable[tuple[str, str, str]]) -> None:
    markup = '<div class="rr-metric-strip">'
    for label, value, note in items:
        markup += (
            '<div class="rr-strip-item">'
            f"<small>{html.escape(label)}</small>"
            f"<strong>{html.escape(value)}</strong>"
            f"<span>{html.escape(note)}</span></div>"
        )
    markup += "</div>"
    st.html(markup)


def priority_queue(rows: Iterable[dict[str, str]]) -> None:
    markup = (
        '<div class="rr-queue">'
        '<div class="rr-queue-row rr-queue-head">'
        "<span>순위</span><span>리뷰어</span><span>모델 판단</span>"
        "<span>상대 모델 점수</span><span>핵심 신호</span>"
        "<span>권장 검토</span><span></span></div>"
    )
    for row in rows:
        user_id = html.escape(row["user_id"])
        href = f"/reviewers?reviewer={quote(row['user_id'], safe='')}"
        retained = max(0.0, min(1.0, float(row.get("retained_score", 0))))
        weakened = max(0.0, min(1.0, float(row.get("weakened_score", 0))))
        stopped = max(0.0, min(1.0, float(row.get("stopped_score", 0))))
        judgment = str(row.get("model_judgment", "—"))
        judgment_class = (
            "stopped"
            if "중단" in judgment
            else "weakened"
            if "약화" in judgment
            else "retained"
        )
        markup += (
            f'<a class="rr-queue-row" href="{href}" target="_self">'
            f'<span class="rr-rank">{html.escape(row["rank"])}</span>'
            f"<strong>{user_id}</strong>"
            f'<span class="rr-state rr-state--{judgment_class}">'
            f"{html.escape(judgment)}</span>"
            '<span class="rr-score-lanes">'
            f'<i><small>유</small><b class="is-retained" style="width:{retained * 100:.1f}%"></b></i>'
            f'<i><small>약</small><b class="is-weakened" style="width:{weakened * 100:.1f}%"></b></i>'
            f'<i><small>중</small><b class="is-stopped" style="width:{stopped * 100:.1f}%"></b></i>'
            "</span>"
            f"<span>{html.escape(row['core_signal'])}</span>"
            f"<span>{html.escape(row['action'])}</span>"
            '<span class="rr-arrow">→</span></a>'
        )
    markup += "</div>"
    st.html(markup)


def signal_bars(items: Iterable[tuple[str, int]]) -> None:
    prepared = list(items)
    maximum = max((value for _, value in prepared), default=1)
    markup = '<div class="rr-signal-bars">'
    for label, value in prepared:
        width = max(4.0, value / maximum * 100)
        markup += (
            '<div class="rr-signal-bar">'
            f"<div><span>{html.escape(label)}</span><strong>{value:,}명</strong></div>"
            f'<i><b style="width:{width:.1f}%"></b></i></div>'
        )
    markup += "</div>"
    st.html(markup)


def change_story(items: Iterable[dict[str, object]]) -> None:
    markup = '<div class="rr-change-story">'
    for item in items:
        label = str(item["label"])
        before = str(item["before"])
        after = str(item["after"])
        delta = str(item["delta"])
        delta_tone = str(item.get("delta_tone", "warning"))
        before_value = float(item.get("before_value", 0))
        after_value = float(item.get("after_value", 0))
        maximum = max(before_value, after_value, 1.0)
        before_height = max(8.0, before_value / maximum * 100)
        after_height = max(8.0, after_value / maximum * 100)
        icon = str(item.get("icon", "query_stats"))
        markup += (
            '<div class="rr-change-row">'
            '<div class="rr-change-label">'
            f"<span>{svg_icon(icon)}</span>"
            f"<strong>{html.escape(label)}</strong></div>"
            '<div class="rr-change-value rr-change-value--before">'
            f"<small>과거</small><strong>{html.escape(before)}</strong></div>"
            '<div class="rr-change-viz">'
            f'<i class="before" style="height:{before_height:.1f}%"></i>'
            '<span></span>'
            f'<i class="after" style="height:{after_height:.1f}%"></i></div>'
            '<div class="rr-change-value rr-change-value--after">'
            f"<small>최근</small><strong>{html.escape(after)}</strong></div>"
            f'<div class="rr-change-delta is-{html.escape(delta_tone)}">{html.escape(delta)}</div></div>'
        )
    markup += "</div>"
    st.html(markup)


def operations_flow() -> None:
    st.html(
        """
        <section class="rr-flow">
          <div class="rr-flow-step is-done"><b>1</b><strong>검토</strong><span>통합 큐 확인</span></div>
          <i></i>
          <div class="rr-flow-step is-done"><b>2</b><strong>관리자 판단</strong><span>활동 근거 확인</span></div>
          <i></i>
          <div class="rr-flow-step is-done"><b>3</b><strong>플레이북</strong><span>전략 후보 선택</span></div>
          <i class="is-future"></i>
          <div class="rr-flow-step is-future"><b>4</b><strong>CRM 실행</strong><span>고도화 예정</span></div>
          <i class="is-future"></i>
          <div class="rr-flow-step is-future"><b>5</b><strong>성과 학습</strong><span>고도화 예정</span></div>
        </section>
        """
    )


def decision_band(items: Iterable[tuple[str, str, str]]) -> None:
    markup = '<div class="rr-decision-band">'
    for index, (label, value, note) in enumerate(items, start=1):
        markup += (
            '<div class="rr-decision-cell">'
            f"<b>{index}</b><small>{html.escape(label)}</small>"
            f"<strong>{html.escape(value)}</strong>"
            f"<span>{html.escape(note)}</span></div>"
        )
    markup += "</div>"
    st.html(markup)


def capability_grid(
    items: Iterable[tuple[str, str, str]],
) -> None:
    markup = '<div class="rr-capability-grid">'
    for title, copy, status in items:
        markup += (
            '<div class="rr-capability">'
            f"{status_badge(status)}"
            f"<strong>{html.escape(title)}</strong>"
            f"<p>{html.escape(copy)}</p></div>"
        )
    markup += "</div>"
    st.html(markup)


def timeline_band(items: Iterable[tuple[str, str, str]]) -> None:
    markup = '<div class="rr-timeline-band">'
    for index, (year, label, copy) in enumerate(items, start=1):
        markup += (
            '<div class="rr-time-point">'
            f"<b>{html.escape(year)}</b><i>{index}</i>"
            f"<strong>{html.escape(label)}</strong>"
            f"<span>{html.escape(copy)}</span></div>"
        )
    markup += "</div>"
    st.html(markup)


def section_header(
    title: str,
    description: str | None = None,
    status: str | None = None,
) -> None:
    copy = (
        f"<p>{html.escape(description)}</p>"
        if description
        else ""
    )
    badge = status_badge(status) if status else ""
    st.html(
        f"""
        <div class="rr-section">
          <div><h2>{html.escape(title)}</h2>{copy}</div>
          <div>{badge}</div>
        </div>
        """
    )


def divider_list(items: Iterable[tuple[str, str]]) -> None:
    rows = "".join(
        '<div class="rr-divider-row">'
        f"<strong>{html.escape(str(label))}</strong>"
        f"<small>{html.escape(str(value))}</small>"
        "</div>"
        for label, value in items
    )
    st.html(f'<div class="rr-divider-list">{rows}</div>')


def empty_state(
    title: str,
    message: str,
    status: str = "데이터 연결 필요",
    details: Iterable[tuple[str, str]] | None = None,
) -> None:
    detail_html = ""
    if details:
        detail_html = '<div class="rr-divider-list" style="margin-top:.8rem">'
        for label, value in details:
            detail_html += (
                '<div class="rr-divider-row">'
                f"<strong>{html.escape(str(label))}</strong>"
                f"<small>{html.escape(str(value))}</small></div>"
            )
        detail_html += "</div>"
    st.html(
        f"""
        <div class="rr-empty">
          {status_badge(status)}
          <h3>{html.escape(title)}</h3>
          <p>{html.escape(message)}</p>
          {detail_html}
        </div>
        """
    )


def profile_header(
    *,
    user_id: str,
    rank: int,
    model_judgment: str,
    retained_score: float,
    weakened_score: float,
    stopped_score: float,
    selected_for_review: bool,
    selection_year: int,
    target_year: int,
) -> None:
    target_label = "통합 상위 20% 검토 대상" if selected_for_review else "일반 모니터링"
    st.html(
        f"""
        <section class="rr-profile-head">
          <div class="rr-profile-identity">
            <div class="rr-profile-id">{html.escape(user_id)}</div>
            <div class="rr-profile-fact"><span>통합 우선순위</span><strong>{rank:,}위</strong></div>
            <div class="rr-profile-fact"><span>모델 판단</span><strong>{html.escape(model_judgment)}</strong></div>
            <div class="rr-profile-tier">{html.escape(target_label)}</div>
          </div>
          <div class="rr-profile-meta">
            <span>선정 {selection_year} · 관찰 {selection_year + 1} · 검증 {target_year}</span>
            <small>클래스 점수는 확률이 아닌 상대 모델 점수입니다.</small>
          </div>
        </section>
        <div class="rr-profile-scores">
          <div><span>유지 점수</span><i><b class="is-retained" style="width:{retained_score * 100:.1f}%"></b></i><strong>{retained_score:.3f}</strong></div>
          <div><span>약화 점수</span><i><b class="is-weakened" style="width:{weakened_score * 100:.1f}%"></b></i><strong>{weakened_score:.3f}</strong></div>
          <div><span>중단 점수</span><i><b class="is-stopped" style="width:{stopped_score * 100:.1f}%"></b></i><strong>{stopped_score:.3f}</strong></div>
        </div>
        """
    )


def evidence_list(items: Iterable[tuple[str, str, str]]) -> None:
    markup = ""
    for index, (title, evidence, group) in enumerate(items, start=1):
        markup += (
            '<div class="rr-evidence">'
            f"<strong>{index}</strong>"
            f"<div><strong>{html.escape(title)}</strong>"
            f"<p>{html.escape(evidence)}</p></div>"
            f"<small>{html.escape(group)}</small>"
            '<i></i></div>'
        )
    st.html(markup)


def action_rail(
    *,
    title: str,
    description: str,
    steps: Iterable[tuple[str, str]],
) -> None:
    markup = (
        '<div class="rr-action-rail">'
        '<div class="rr-eyebrow">Recommended playbook</div>'
        f"<h2>{html.escape(title)}</h2>"
        f'<p class="rr-copy">{html.escape(description)}</p>'
    )
    for label, value in steps:
        markup += (
            '<div class="rr-action-step">'
            f"<b>{len(markup.split('rr-action-step'))}</b>"
            f"<div><small>{html.escape(label)}</small>"
            f"<strong>{html.escape(value)}</strong></div></div>"
        )
    markup += "</div>"
    st.html(markup)


def future_integration(
    title: str,
    requirement: str,
) -> None:
    st.html(
        f"""
        <section class="rr-future-module">
          <div>
            <span>{svg_icon("groups")}</span>
            <div><strong>{html.escape(title)}</strong><p>자동 배정 및 성과 추적 영역</p></div>
          </div>
          {status_badge("고도화 예정")}
          <small>{svg_icon("lock")}
          필요 데이터 · {html.escape(requirement)}</small>
        </section>
        """
    )


def render_warnings(warnings: list[str]) -> None:
    if not warnings:
        return
    with st.expander(
        f"데이터 연결 상태 · {len(warnings)}건",
        icon=":material/database:",
        expanded=False,
    ):
        for warning in warnings:
            st.warning(warning, icon=":material/info:")


def footer(data_mode: str) -> None:
    mode_label = {
        "project": "Project data",
        "hybrid": "Hybrid data",
        "demo": "Demo data",
    }.get(data_mode, data_mode)
    st.caption(
        "Reviewer Retention · "
        f"{mode_label} · 클래스 점수는 보정 확률이 아니며 통합 점수는 운영 우선순위에 사용합니다."
    )
