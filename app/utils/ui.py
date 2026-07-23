from __future__ import annotations

import html

import streamlit as st


COLORS = {
    "ink": "#17222E",
    "muted": "#667381",
    "orange": "#EF5B36",
    "coral": "#F28B66",
    "teal": "#1F8A7A",
    "cream": "#F6F4EF",
    "white": "#FFFFFF",
    "line": "#E7E2D9",
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #F6F4EF; }
        [data-testid="stSidebar"] { background: #17222E; }
        [data-testid="stSidebar"] * { color: #F7F5F0; }
        [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.14); }
        .block-container { max-width: 1280px; padding-top: 2rem; padding-bottom: 4rem; }
        h1, h2, h3 { color: #17222E; letter-spacing: -0.035em; }
        .hero {
            padding: 2.2rem 2.4rem; border-radius: 28px;
            background: linear-gradient(120deg, #17222E 0%, #24394A 62%, #1F8A7A 130%);
            color: white; box-shadow: 0 18px 50px rgba(23,34,46,.14); margin-bottom: 1.4rem;
        }
        .hero-kicker { color: #FF9A74; font-size: .78rem; font-weight: 800; letter-spacing: .16em; }
        .hero h1 { color: white; font-size: 2.45rem; line-height: 1.08; margin: .55rem 0 .7rem; }
        .hero p { color: rgba(255,255,255,.76); font-size: 1.02rem; max-width: 760px; margin: 0; }
        .metric-card {
            background: white; border: 1px solid #E7E2D9; border-radius: 20px;
            padding: 1.15rem 1.25rem; box-shadow: 0 8px 28px rgba(23,34,46,.055); min-height: 120px;
        }
        .metric-label { color: #71808D; font-size: .78rem; font-weight: 700; letter-spacing: .06em; }
        .metric-value { color: #17222E; font-size: 1.75rem; font-weight: 850; margin-top: .35rem; }
        .metric-note { color: #84909A; font-size: .78rem; margin-top: .3rem; }
        .insight-card { background: white; border-radius: 18px; padding: 1.15rem 1.25rem; border-left: 5px solid #EF5B36; margin: .55rem 0; }
        .insight-card.teal { border-left-color: #1F8A7A; }
        .insight-title { font-weight: 800; color: #17222E; margin-bottom: .25rem; }
        .insight-body { color: #667381; line-height: 1.55; font-size: .91rem; }
        .section-kicker { color: #EF5B36; font-size: .72rem; font-weight: 850; letter-spacing: .14em; margin-top: 1.2rem; }
        .mode-pill { display:inline-block; padding:.3rem .6rem; border-radius:999px; font-size:.7rem; font-weight:800; background:#FFF0EA; color:#D94C29; }
        .mode-pill.live { background:#E5F6F2; color:#147163; }
        div[data-testid="stDataFrame"] { border: 1px solid #E7E2D9; border-radius: 16px; overflow: hidden; }
        .stTabs [data-baseweb="tab-list"] { gap: .4rem; }
        .stTabs [data-baseweb="tab"] { border-radius: 999px; padding: .55rem 1rem; background: #ECE8E0; }
        .stTabs [aria-selected="true"] { background: #17222E !important; color: white !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_context(is_demo: bool) -> None:
    st.sidebar.markdown("### Yelp Reviewer Lab")
    st.sidebar.caption("Power reviewer churn · validation prototype")
    st.sidebar.divider()
    badge = "DEMO DATA" if is_demo else "LIVE V01 DATA"
    klass = "" if is_demo else " live"
    st.sidebar.markdown(
        f'<span class="mode-pill{klass}">{badge}</span>', unsafe_allow_html=True
    )
    st.sidebar.markdown("\n")
    st.sidebar.caption("2017 파워 리뷰어 선정  →  2018 루틴 관찰  →  2019 이탈 확인")
    st.sidebar.divider()
    st.sidebar.caption("이 화면은 분석 검증용이며 모델 예측 확률을 제공하지 않습니다.")


def hero(kicker: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">{html.escape(kicker)}</div>
          <h1>{html.escape(title)}</h1>
          <p>{html.escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(kicker: str, title: str, body: str | None = None) -> None:
    st.markdown(f'<div class="section-kicker">{html.escape(kicker)}</div>', unsafe_allow_html=True)
    st.subheader(title)
    if body:
        st.caption(body)


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{html.escape(label)}</div>
          <div class="metric-value">{html.escape(value)}</div>
          <div class="metric-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight(title: str, body: str, tone: str = "orange") -> None:
    extra = " teal" if tone == "teal" else ""
    st.markdown(
        f"""
        <div class="insight-card{extra}">
          <div class="insight-title">{html.escape(title)}</div>
          <div class="insight-body">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
