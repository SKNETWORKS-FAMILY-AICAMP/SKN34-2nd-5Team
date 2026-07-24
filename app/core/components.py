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
    "현재 제외": "excluded",
    "긴급 검토": "critical",
}


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
        "<span>순위</span><span>리뷰어</span><span>위험 유형</span>"
        "<span>활동 변화</span><span>권장 행동</span><span></span></div>"
    )
    for row in rows:
        user_id = html.escape(row["user_id"])
        href = f"/reviewers?reviewer={quote(row['user_id'], safe='')}"
        before_value = float(row.get("before_value", 0))
        after_value = float(row.get("after_value", 0))
        maximum = max(before_value, after_value, 1.0)
        before_width = max(5.0, before_value / maximum * 100)
        after_width = max(5.0, after_value / maximum * 100)
        markup += (
            f'<a class="rr-queue-row" href="{href}" target="_self">'
            f'<span class="rr-rank">{html.escape(row["rank"])}</span>'
            f"<strong>{user_id}</strong>"
            f'<span class="rr-risk">{html.escape(row["risk_type"])}</span>'
            '<span class="rr-queue-change">'
            '<i class="rr-queue-track">'
            f'<b style="width:{before_width:.1f}%"></b>'
            f'<em style="width:{after_width:.1f}%"></em></i>'
            f"<small>{html.escape(row['change'])}</small></span>"
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
        before_value = float(item.get("before_value", 0))
        after_value = float(item.get("after_value", 0))
        maximum = max(before_value, after_value, 1.0)
        before_height = max(8.0, before_value / maximum * 100)
        after_height = max(8.0, after_value / maximum * 100)
        icon = str(item.get("icon", "query_stats"))
        markup += (
            '<div class="rr-change-row">'
            '<div class="rr-change-label">'
            f'<span class="material-symbols-rounded">{html.escape(icon)}</span>'
            f"<strong>{html.escape(label)}</strong></div>"
            '<div class="rr-change-value rr-change-value--before">'
            f"<small>과거</small><strong>{html.escape(before)}</strong></div>"
            '<div class="rr-change-viz">'
            f'<i class="before" style="height:{before_height:.1f}%"></i>'
            '<span></span>'
            f'<i class="after" style="height:{after_height:.1f}%"></i></div>'
            '<div class="rr-change-value rr-change-value--after">'
            f"<small>최근</small><strong>{html.escape(after)}</strong></div>"
            f'<div class="rr-change-delta">{html.escape(delta)}</div></div>'
        )
    markup += "</div>"
    st.html(markup)


def operations_flow() -> None:
    st.html(
        """
        <section class="rr-flow">
          <div class="rr-flow-step is-done"><b>1</b><strong>검토</strong><span>신호 확인 및 우선순위 결정</span></div>
          <i></i>
          <div class="rr-flow-step is-done"><b>2</b><strong>플레이북</strong><span>리텐션 전략 선택</span></div>
          <i class="is-future"></i>
          <div class="rr-flow-step is-future"><b>3</b><strong>CRM 연동</strong><span>고도화 예정</span></div>
        </section>
        """
    )


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
    score: float,
    tier: str,
    selection_year: int,
    target_year: int,
) -> None:
    st.html(
        f"""
        <section class="rr-profile-head">
          <div class="rr-profile-identity">
            <div class="rr-profile-id">{html.escape(user_id)}</div>
            <div class="rr-profile-fact"><span>위험 순위</span><strong>{rank:,}위</strong></div>
            <div class="rr-profile-fact"><span>모델 점수</span><strong>{score:.4f}</strong></div>
            <div class="rr-profile-tier">{html.escape(tier)}</div>
          </div>
          <div class="rr-profile-meta">
            <span>선정 {selection_year} · 관찰 {selection_year + 1} · 검증 {target_year}</span>
            <small>점수는 확률이 아닌 위험 순위용입니다.</small>
          </div>
        </section>
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
            <span class="material-symbols-rounded">groups</span>
            <div><strong>{html.escape(title)}</strong><p>자동 배정 및 성과 추적 영역</p></div>
          </div>
          {status_badge("외부 연동 필요")}
          <small><span class="material-symbols-rounded">lock</span>
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
        f"{mode_label} · 위험 점수는 보정 확률이 아닌 운영 우선순위 점수입니다."
    )
