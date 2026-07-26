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


def policy_panel(
    *,
    target_users: int,
    captured_users: int,
    precision: float,
    recall: float,
    recall_ceiling: float,
    lift: float,
    weakened_total: int,
    stopped_total: int,
) -> None:
    lift_fill_pct = max(4.0, min(100.0, lift / 2.0 * 100))
    st.html(
        f"""
        <div class="rr-card rr-policy-card">
          <h3>이 큐는 왜 우선인가</h3>
          <p class="rr-policy-sub">사후 Test 검증 결과이며, 무작위 선택 대비 정밀도가 높습니다.</p>

          <div class="rr-policy-row">
            <span class="rr-p-label">검토 용량</span>
            <span class="rr-p-value">{target_users:,}명</span>
          </div>
          <div class="rr-policy-row">
            <span class="rr-p-label">상태 상실 포착</span>
            <span class="rr-p-value">{captured_users:,}명</span>
          </div>
          <div class="rr-policy-row">
            <span class="rr-p-label">정밀도</span>
            <span class="rr-p-value is-good">{precision:.1%}</span>
          </div>

          <div class="rr-policy-row" style="display:block">
            <div style="display:flex;align-items:baseline;justify-content:space-between">
              <span class="rr-p-label">재현율</span>
              <span class="rr-p-value">{recall:.1%}</span>
            </div>
            <p class="rr-policy-caption">한 번에 20%만 볼 수 있어 최대로 잡아도 {recall_ceiling:.1%}까지가 한계입니다</p>
          </div>

          <div class="rr-lift-row">
            <div class="rr-lift-top">
              <span>무작위로 뽑을 때보다</span>
              <span class="rr-p-value">{lift:.2f}배 정확</span>
            </div>
            <div class="rr-lift-track">
              <div class="rr-lift-fill" style="width:{lift_fill_pct:.1f}%"></div>
              <div class="rr-lift-marker"></div>
            </div>
          </div>

          <div class="rr-policy-split">
            <span>약화 우세 {weakened_total:,}명</span>
            <span>중단 우세 {stopped_total:,}명</span>
          </div>
        </div>
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


def priority_queue(rows: Iterable[dict[str, object]]) -> None:
    markup = '<div class="rr-card">'
    for index, row in enumerate(rows):
        user_id = html.escape(str(row["user_id"]))
        href = f"/reviewers?reviewer={quote(str(row['user_id']), safe='')}"
        judgment = str(row.get("model_judgment", "—"))
        judgment_class = (
            "stopped"
            if "중단" in judgment
            else "weakened"
            if "약화" in judgment
            else "retained"
        )
        tier = "strong" if index < 2 else "soft"
        markup += (
            f'<a class="rr-qrow" href="{href}" target="_self">'
            f'<span class="rr-qrank rr-qrank--{judgment_class}-{tier}">{index + 1}</span>'
            f'<span class="rr-qname">{user_id}</span>'
            f'<span class="rr-state rr-state--{judgment_class}">'
            f"{html.escape(judgment)}</span>"
            f'<span class="rr-qchange">{html.escape(str(row.get("change_text", "")))}</span>'
            f'<span class="rr-qaction">{html.escape(str(row.get("action", "")))}</span>'
            '<i class="rr-qarrow">→</i></a>'
        )
    markup += "</div>"
    st.html(markup)


def reviewer_list(rows: Iterable[dict[str, object]]) -> None:
    markup = (
        '<div class="rr-card rr-worklist-card rr-worklist-scroll">'
        '<div class="rr-wrow-head">'
        "<span>순위</span><span>리뷰어</span><span>모델 판단</span>"
        "<span>핵심 변화</span><span>핵심 신호</span><span>권장 검토</span><span></span>"
        "</div>"
    )
    for row in rows:
        user_id = html.escape(str(row["user_id"]))
        href = f"/reviewers?reviewer={quote(str(row['user_id']), safe='')}"
        judgment = str(row.get("model_judgment", "—"))
        judgment_class = (
            "stopped"
            if "중단" in judgment
            else "weakened"
            if "약화" in judgment
            else "retained"
        )
        completed_label = row.get("completed_label")
        if completed_label:
            action_html = (
                '<span class="rr-qaction-badge rr-qaction-badge--done">'
                f'✓ {html.escape(str(completed_label))}</span>'
            )
        else:
            action_html = (
                '<span class="rr-qaction-badge">'
                f'{html.escape(str(row.get("action", "")))}</span>'
            )
        metrics = [str(m) for m in row.get("metrics", []) if m]
        metrics_text = html.escape(" · ".join(metrics))
        signal_label = row.get("signal_label")
        signal_html = (
            f'<span class="rr-qsignal-tag">{html.escape(str(signal_label))}</span>'
            if signal_label
            else "<span></span>"
        )
        row_class = "rr-wrow rr-wrow--done" if completed_label else "rr-wrow"
        markup += (
            f'<a class="{row_class}" href="{href}" target="_self">'
            f'<span class="rr-qrank-plain">{html.escape(str(row.get("rank_label", "")))}</span>'
            f'<span class="rr-wname">{user_id}</span>'
            f'<span class="rr-state rr-state--{judgment_class}">'
            f"{html.escape(judgment)}</span>"
            f'<span class="rr-wmetric">{metrics_text}</span>'
            f"{signal_html}"
            f"{action_html}"
            '<i class="rr-qarrow">→</i>'
            "</a>"
        )
    markup += "</div>"
    st.html(markup)


def stat_card_row(items: Iterable[tuple[str, str, str | None]]) -> None:
    markup = '<div class="rr-stat-row">'
    for label, value, tone in items:
        tone_class = f" rr-stat-value--{tone}" if tone else ""
        markup += (
            '<div class="rr-card rr-stat-card">'
            f'<div class="rr-stat-label">{html.escape(label)}</div>'
            f'<div class="rr-stat-value{tone_class}">{html.escape(value)}</div>'
            "</div>"
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
    markup = '<div class="rr-change-grid">'
    for item in items:
        label = str(item["label"])
        before = str(item["before"])
        after = str(item["after"])
        delta = str(item["delta"])
        delta_tone = str(item.get("delta_tone", "warning"))
        icon = str(item.get("icon", "query_stats"))
        markup += (
            '<div class="rr-change-tile">'
            '<div class="rr-change-tile-label">'
            f"{svg_icon(icon)}<span>{html.escape(label)}</span></div>"
            '<div class="rr-change-tile-values">'
            f"<s>{html.escape(before)}</s>"
            '<i class="rr-qarrow">→</i>'
            f"<strong>{html.escape(after)}</strong></div>"
            f'<div class="rr-change-tile-delta is-{html.escape(delta_tone)}">{html.escape(delta)}</div>'
            "</div>"
        )
    markup += "</div>"
    st.html(markup)


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
    total_reviewers: int,
    model_judgment: str,
    retained_score: float,
    weakened_score: float,
    stopped_score: float,
    selected_for_review: bool,
    selection_year: int,
    target_year: int,
) -> None:
    target_label = "통합 상위 20% 검토 대상" if selected_for_review else "일반 모니터링"
    judgment_class = (
        "stopped"
        if "중단" in model_judgment
        else "weakened"
        if "약화" in model_judgment
        else "retained"
    )
    top_percent = (rank / total_reviewers * 100) if total_reviewers else 0.0
    percent_label = "상위 0.1% 이내" if top_percent < 0.1 else f"상위 {top_percent:.1f}%"
    st.html(
        f"""
        <div class="rr-profile-card">
          <div class="rr-profile-head">
            <div>
              <div class="rr-profile-id">{html.escape(user_id)}</div>
              <div class="rr-profile-badges">
                <span class="rr-pill">전체 {total_reviewers:,}명 중 {rank:,}위 · {percent_label}</span>
                <span class="rr-state rr-state--{judgment_class}">{html.escape(model_judgment)}</span>
                <span class="rr-pill">{html.escape(target_label)}</span>
              </div>
            </div>
            <div class="rr-profile-meta">
              <span>선정 {selection_year} · 관찰 {selection_year + 1} · 검증 {target_year}</span>
              <small>클래스 점수는 확률이 아닌 상대 모델 점수입니다.</small>
            </div>
          </div>
          <div class="rr-score-rows">
            <div class="rr-score-row"><span>유지</span><i><b class="is-retained" style="width:{max(retained_score * 100, 2.0):.1f}%"></b></i><strong>{retained_score:.3f}</strong></div>
            <div class="rr-score-row"><span>약화</span><i><b class="is-weakened" style="width:{max(weakened_score * 100, 2.0):.1f}%"></b></i><strong>{weakened_score:.3f}</strong></div>
            <div class="rr-score-row"><span>중단</span><i><b class="is-stopped" style="width:{max(stopped_score * 100, 2.0):.1f}%"></b></i><strong>{stopped_score:.3f}</strong></div>
          </div>
        </div>
        """
    )


def evidence_list(items: Iterable[tuple[str, str, str]]) -> None:
    markup = '<div class="rr-evidence-card">'
    for index, (title, evidence, group) in enumerate(items, start=1):
        markup += (
            '<div class="rr-evidence">'
            f"<strong>{index}</strong>"
            "<div>"
            f'<span class="rr-evidence-title">{html.escape(title)}</span>'
            f"<p>{html.escape(evidence)}</p>"
            f'<span class="rr-qsignal-tag">{html.escape(group)}</span>'
            "</div></div>"
        )
    markup += "</div>"
    st.html(markup)


def action_rail(
    *,
    title: str,
    description: str,
    steps: Iterable[tuple[str, str]],
) -> None:
    markup = (
        '<div class="rr-action-card">'
        '<div class="rr-eyebrow">Recommended playbook</div>'
        f"<h2>{html.escape(title)}</h2>"
        f'<p class="rr-copy">{html.escape(description)}</p>'
    )
    for label, value in steps:
        markup += (
            '<div class="rr-action-step">'
            f"<small>{html.escape(label)}</small>"
            f"<strong>{html.escape(value)}</strong>"
            "</div>"
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
