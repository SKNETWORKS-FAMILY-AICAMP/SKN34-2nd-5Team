from __future__ import annotations

import streamlit as st


COLORS = {
    "ink": "#17211D",
    "muted": "#68736D",
    "canvas": "#F7F8F5",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F4F1",
    "line": "#DDE4DF",
    "primary": "#137A5A",
    "primary_alt": "#4C987C",
    "coral": "#E15D47",
    "teal": "#2F7D61",
    "navy": "#185C46",
    "amber": "#A66A18",
    "critical": "#E15D47",
    "focus": "#A66A18",
    "watch": "#356A78",
    "normal": "#66746D",
    "purple": "#70567B",
}


CSS = """
<style>
:root {
  --rr-ink: #17211D;
  --rr-muted: #68736D;
  --rr-line: #DDE4DF;
  --rr-primary: #137A5A;
  --rr-primary-alt: #4C987C;
  --rr-soft: #F1F4F1;
  --rr-critical: #E15D47;
  --rr-focus: #A66A18;
  --rr-watch: #356A78;
}

[data-testid="stAppViewContainer"] {
  background: #F7F8F5;
}

[data-testid="stHeader"] {
  display: none;
}

[data-testid="stSidebar"] {
  display: none;
}

[data-testid="stMain"] .block-container {
  max-width: 1580px;
  padding-top: .35rem;
  padding-inline: 2.1rem;
  padding-bottom: 4rem;
}

[data-testid="stToolbar"], #MainMenu, footer {
  visibility: hidden;
}

.st-key-product_header {
  position: sticky;
  top: 0;
  z-index: 999;
  min-height: 62px;
  padding: .5rem 0;
  margin: 0 0 .4rem;
  background: rgba(247, 248, 245, .96);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--rr-line);
}

.st-key-product_header [data-testid="stHtml"] {
  flex: 0 0 auto;
}

.product-brand {
  display: flex;
  align-items: center;
  gap: .65rem;
  color: var(--rr-ink);
  font-weight: 750;
  letter-spacing: -.02em;
  min-width: 230px;
  font-size: 1rem;
}

.product-mark {
  width: 22px;
  height: 22px;
  border-radius: 7px 7px 7px 2px;
  background: var(--rr-primary);
  position: relative;
}

.product-mark:after {
  content: "";
  position: absolute;
  width: 6px;
  height: 6px;
  border: 2px solid white;
  border-radius: 50%;
  left: 6px;
  top: 6px;
}

.product-mode {
  display: flex;
  align-items: center;
  gap: .65rem;
  color: var(--rr-muted);
  font-size: .75rem;
  margin-left: auto;
}

.product-mode span:first-child {
  padding: .18rem .5rem;
  border-radius: 999px;
  background: var(--rr-ink);
  color: white;
  font-weight: 700;
}

.st-key-product_header [data-testid="stPageLink"] a {
  min-height: 36px;
  padding: .52rem .82rem;
  border-radius: 0;
  color: var(--rr-muted);
  font-size: .75rem;
  font-weight: 650;
  text-decoration: none;
}

.st-key-product_header [data-testid="stPageLink"] a:hover {
  color: var(--rr-primary);
  background: #EDF3EF;
}

.st-key-product_header [data-testid="stPageLink"] a[aria-current="page"] {
  color: var(--rr-primary);
  background: transparent;
  box-shadow: inset 0 -2px 0 var(--rr-primary);
}

.rr-page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.4rem;
  padding: 1.35rem .35rem 1.2rem;
  border-bottom: 1px solid var(--rr-line);
  margin-bottom: 1rem;
}

.rr-eyebrow {
  color: var(--rr-primary-alt);
  font-size: .68rem;
  font-weight: 750;
  letter-spacing: .11em;
  text-transform: uppercase;
}

.rr-title {
  color: var(--rr-ink);
  font-size: clamp(2rem, 3vw, 2.65rem);
  font-weight: 760;
  line-height: 1.18;
  letter-spacing: -.045em;
  margin-top: .3rem;
}

.rr-copy {
  max-width: 780px;
  color: var(--rr-muted);
  font-size: .85rem;
  line-height: 1.65;
  margin-top: .42rem;
}

.rr-badges {
  display: flex;
  gap: .35rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.rr-badge {
  display: inline-flex;
  align-items: center;
  gap: .32rem;
  border-radius: 999px;
  padding: .24rem .55rem;
  font-size: .65rem;
  font-weight: 700;
  white-space: nowrap;
  background: var(--rr-soft);
  color: var(--rr-muted);
}

.rr-badge:before {
  content: "";
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.rr-badge--now { color: var(--rr-primary-alt); background: #E3F1EA; }
.rr-badge--rule { color: var(--rr-focus); background: #FAEFD9; }
.rr-badge--data { color: var(--rr-watch); background: #E6EFF1; }
.rr-badge--definition { color: #70567B; background: #EEE8F1; }
.rr-badge--analysis { color: #765D35; background: #F4EEE3; }
.rr-badge--external { color: #70567B; background: #EEE8F1; }
.rr-badge--excluded { color: #69716D; background: #ECEFEC; }
.rr-badge--critical { color: var(--rr-critical); background: #F7E8E5; }

.rr-brief {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(260px, .6fr);
  gap: 2rem;
  align-items: center;
  padding: 1.7rem 0;
}

.rr-brief-main {
  color: var(--rr-ink);
  font-size: clamp(1.35rem, 2.5vw, 2rem);
  line-height: 1.42;
  letter-spacing: -.035em;
  font-weight: 680;
}

.rr-brief-main strong { color: var(--rr-critical); }

.rr-brief-note {
  color: var(--rr-muted);
  font-size: .76rem;
  line-height: 1.65;
  padding-left: 1rem;
  border-left: 2px solid var(--rr-primary);
}

.rr-metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-top: 1px solid var(--rr-ink);
  border-bottom: 1px solid var(--rr-line);
  margin: .2rem 0 1.55rem;
  background: rgba(255,255,255,.55);
}

.rr-strip-item {
  display: grid;
  gap: .2rem;
  padding: .85rem 1.4rem;
  text-align: center;
}

.rr-strip-item + .rr-strip-item {
  border-left: 1px solid var(--rr-line);
  padding-left: 1.4rem;
}

.rr-strip-item small, .rr-strip-item span {
  color: var(--rr-muted);
  font-size: .68rem;
}

.rr-strip-item strong {
  color: var(--rr-ink);
  font-size: 1.8rem;
  letter-spacing: -.04em;
}

.rr-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  margin: 2rem 0 .7rem;
}

.rr-section h2 {
  color: var(--rr-ink);
  font-size: 1.16rem;
  letter-spacing: -.025em;
  margin: 0;
}

.rr-section p {
  color: var(--rr-muted);
  font-size: .76rem;
  margin: .2rem 0 0;
}

.rr-queue {
  border-top: 1px solid var(--rr-ink);
}

.rr-queue-row {
  display: grid;
  grid-template-columns: 40px minmax(155px, .8fr) 105px minmax(175px, 1fr) minmax(170px, .9fr) 24px;
  align-items: center;
  gap: .75rem;
  min-height: 58px;
  padding: .55rem .35rem;
  border-bottom: 1px solid var(--rr-line);
  color: var(--rr-ink);
  font-size: .75rem;
  text-decoration: none;
  transition: background .16s ease, padding .16s ease;
}

.rr-queue-row:not(.rr-queue-head):hover {
  background: #F0F5F1;
  padding-inline: .5rem;
}

.rr-queue-head {
  min-height: 34px;
  color: var(--rr-muted);
  font-size: .62rem;
}

.rr-rank { color: var(--rr-muted); }
.rr-risk { color: var(--rr-critical); font-weight: 700; }
.rr-arrow { color: var(--rr-primary); font-weight: 700; text-align: right; }

.rr-queue-change {
  display: grid;
  grid-template-columns: minmax(80px, 1fr) auto;
  align-items: center;
  gap: .7rem;
}

.rr-queue-change small {
  color: var(--rr-muted);
  white-space: nowrap;
}

.rr-queue-track {
  position: relative;
  display: block;
  height: 18px;
  border-left: 1px solid #C6CECA;
}

.rr-queue-track b,
.rr-queue-track em {
  position: absolute;
  left: 0;
  height: 3px;
  display: block;
  border-radius: 2px;
}

.rr-queue-track b { top: 3px; background: #9AA59F; }
.rr-queue-track em { bottom: 3px; background: var(--rr-critical); }

.rr-policy-panel {
  border-top: 1px solid var(--rr-ink);
  border-bottom: 1px solid var(--rr-line);
  padding: 1.05rem .1rem .85rem;
}

.rr-policy-top {
  display: grid;
  grid-template-columns: 1fr 112px;
  align-items: center;
  gap: 1rem;
}

.rr-policy-top h2 {
  margin: .3rem 0 .15rem;
  color: var(--rr-ink);
  font-size: 1.25rem;
  letter-spacing: -.03em;
}

.rr-policy-top p {
  margin: 0;
  color: var(--rr-muted);
  font-size: .72rem;
}

.rr-radial {
  width: 94px;
  height: 94px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(var(--rr-primary) var(--progress), #E3E8E4 0);
  position: relative;
}

.rr-radial:after {
  content: "";
  position: absolute;
  inset: 9px;
  border-radius: 50%;
  background: #F7F8F5;
}

.rr-radial div { z-index: 1; text-align: center; }
.rr-radial strong { display: block; color: var(--rr-primary); font-size: 1.15rem; }
.rr-radial span { display: block; color: var(--rr-muted); font-size: .6rem; }

.rr-policy-lines { margin: .75rem 0 .55rem; }
.rr-policy-lines > div {
  display: grid;
  grid-template-columns: 8px 1fr auto;
  align-items: center;
  gap: .55rem;
  padding: .45rem 0;
  border-bottom: 1px solid var(--rr-line);
  font-size: .72rem;
}
.rr-policy-lines i { width: 7px; height: 7px; border-radius: 50%; background: var(--rr-primary-alt); }
.rr-policy-lines i.is-critical { background: var(--rr-critical); }
.rr-policy-panel > small { color: var(--rr-muted); font-size: .62rem; }

.rr-signal-bars {
  border-top: 1px solid var(--rr-ink);
}

.rr-signal-bar {
  padding: .7rem 0;
  border-bottom: 1px solid var(--rr-line);
}

.rr-signal-bar > div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  font-size: .73rem;
}

.rr-signal-bar i {
  display: block;
  height: 4px;
  background: #E5EAE7;
  margin-top: .45rem;
}

.rr-signal-bar i b {
  display: block;
  height: 100%;
  background: var(--rr-primary);
}

.rr-change-story {
  border-top: 1px solid var(--rr-ink);
}

.rr-change-row {
  display: grid;
  grid-template-columns: 155px 90px minmax(150px, 1fr) 90px 110px;
  align-items: center;
  gap: .9rem;
  min-height: 82px;
  padding: .65rem .1rem;
  border-bottom: 1px solid var(--rr-line);
  font-size: .75rem;
}

.rr-change-label {
  display: flex;
  align-items: center;
  gap: .65rem;
}

.rr-change-label > span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: var(--rr-primary);
  background: #E6F0EA;
  font-size: 1.15rem;
}

.rr-change-value small {
  display: block;
  color: var(--rr-muted);
  font-size: .6rem;
  margin-bottom: .1rem;
}

.rr-change-value strong { font-size: 1.05rem; }
.rr-change-value--before strong { color: var(--rr-primary); }
.rr-change-value--after strong { color: var(--rr-critical); }

.rr-change-viz {
  height: 48px;
  display: grid;
  grid-template-columns: 8px 1fr 8px;
  align-items: end;
  gap: 0;
  position: relative;
}

.rr-change-viz span {
  align-self: center;
  height: 1px;
  background: linear-gradient(90deg, #8E9A93, var(--rr-critical));
  position: relative;
}

.rr-change-viz span:after {
  content: "→";
  position: absolute;
  right: -2px;
  top: -11px;
  color: var(--rr-critical);
  background: #F7F8F5;
  padding-left: 3px;
}

.rr-change-viz i {
  width: 8px;
  min-height: 8px;
  border-radius: 4px 4px 1px 1px;
}
.rr-change-viz i.before { background: var(--rr-primary); }
.rr-change-viz i.after { background: var(--rr-critical); }
.rr-change-delta { color: var(--rr-critical); font-weight: 700; text-align: right; }

.rr-flow {
  display: grid;
  grid-template-columns: 1fr 80px 1fr 80px 1fr;
  align-items: start;
  border-top: 1px solid var(--rr-ink);
  padding-top: 1.25rem;
}

.rr-flow > i {
  height: 1px;
  background: var(--rr-primary);
  margin-top: 17px;
}
.rr-flow > i.is-future { background: repeating-linear-gradient(90deg,#9EAAA3 0 5px,transparent 5px 9px); }
.rr-flow-step { text-align: center; display: grid; justify-items: center; gap: .25rem; }
.rr-flow-step b {
  width: 34px; height: 34px; display: grid; place-items: center;
  border-radius: 50%; color: white; background: var(--rr-primary);
}
.rr-flow-step strong { font-size: .78rem; }
.rr-flow-step span { color: var(--rr-muted); font-size: .65rem; }
.rr-flow-step.is-future b {
  color: var(--rr-primary); background: #F7F8F5; border: 1px dashed var(--rr-primary);
}
.rr-flow-step.is-future span {
  color: var(--rr-primary); background: #E3F1EA; padding: .12rem .4rem; border-radius: 3px;
}

.rr-divider-list {
  border-top: 1px solid var(--rr-ink);
}

.rr-divider-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  padding: .78rem .1rem;
  border-bottom: 1px solid var(--rr-line);
}

.rr-divider-row small {
  color: var(--rr-muted);
}

.rr-empty {
  padding: 1.2rem 0;
  border-top: 1px dashed #AEB8B2;
  border-bottom: 1px dashed #AEB8B2;
}

.rr-empty h3 {
  font-size: .95rem;
  margin: .55rem 0 .25rem;
}

.rr-empty p {
  color: var(--rr-muted);
  font-size: .75rem;
  line-height: 1.6;
  margin: 0;
}

.rr-profile-head {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: .9rem .1rem 1rem;
  border-top: 1px solid var(--rr-ink);
  border-bottom: 1px solid var(--rr-line);
}

.rr-profile-id {
  color: var(--rr-ink);
  font-size: clamp(1.7rem, 2.5vw, 2.35rem);
  font-weight: 740;
  letter-spacing: -.035em;
}

.rr-profile-identity {
  display: flex;
  align-items: center;
  gap: 1.3rem;
}

.rr-profile-fact {
  padding-left: 1.2rem;
  border-left: 1px solid var(--rr-line);
}
.rr-profile-fact span {
  display: block;
  color: var(--rr-muted);
  font-size: .62rem;
}
.rr-profile-fact strong { font-size: 1.05rem; }
.rr-profile-tier { color: var(--rr-critical); font-size: .78rem; font-weight: 750; }
.rr-profile-meta { text-align: right; color: var(--rr-muted); font-size: .68rem; }
.rr-profile-meta small { display: block; margin-top: .22rem; }

.rr-evidence {
  position: relative;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) auto;
  align-items: start;
  gap: .8rem;
  padding: .8rem 0;
  border-bottom: 1px solid var(--rr-line);
}
.rr-evidence > strong {
  width: 26px; height: 26px; border-radius: 50%;
  display: grid; place-items: center; color: white; background: var(--rr-primary);
}
.rr-evidence > i {
  position: absolute;
  left: 12px; top: 39px; bottom: -13px;
  border-left: 1px dashed #AEB8B2;
}
.rr-evidence:last-child > i { display: none; }
.rr-evidence p {
  color: var(--rr-muted);
  font-size: .7rem;
  margin: .15rem 0 0;
}
.rr-evidence > small { color: var(--rr-muted); font-size: .62rem; }

.rr-action-rail {
  padding: 1.2rem 0 0 1.35rem;
  border-top: 1px solid var(--rr-ink);
  border-left: 1px solid var(--rr-line);
  min-height: 100%;
}

.rr-action-rail h2 {
  font-size: 1.4rem;
  line-height: 1.35;
  letter-spacing: -.035em;
  margin: .35rem 0 .25rem;
}

.rr-action-step {
  display: grid;
  grid-template-columns: 30px 1fr;
  align-items: center;
  gap: .8rem;
  padding: .78rem 0;
  border-bottom: 1px solid var(--rr-line);
}
.rr-action-step > b {
  width: 28px; height: 28px; display: grid; place-items: center;
  border-radius: 50%; color: white; background: var(--rr-primary);
}
.rr-action-step small { display: block; color: var(--rr-muted); font-size: .62rem; }
.rr-action-step strong { display: block; margin-top: .1rem; font-size: .76rem; }

.rr-future-module {
  margin-top: .9rem;
  padding: .9rem;
  border: 1px dashed #9EAAA3;
  background: rgba(255,255,255,.35);
}
.rr-future-module > div {
  display: flex; align-items: center; gap: .6rem;
}
.rr-future-module .material-symbols-rounded { color: var(--rr-muted); font-size: 1.5rem; }
.rr-future-module p { margin: .1rem 0 .45rem; color: var(--rr-muted); font-size: .65rem; }
.rr-future-module > small {
  display: flex; align-items: center; gap: .3rem; margin-top: .65rem; padding-top: .55rem;
  border-top: 1px solid var(--rr-line); color: var(--rr-muted); font-size: .6rem;
}
.rr-future-module > small .material-symbols-rounded { font-size: .85rem; }

.rr-roadmap {
  display: grid;
  grid-template-columns: 190px 150px minmax(0, 1fr) minmax(0, 1fr);
  gap: 1rem;
  padding: .8rem .15rem;
  border-bottom: 1px solid var(--rr-line);
  font-size: .76rem;
}

.rr-roadmap--head {
  color: var(--rr-muted);
  font-size: .66rem;
  border-top: 1px solid var(--rr-ink);
}

[data-testid="stMetric"] {
  padding: .8rem 0;
  border-top: 1px solid var(--rr-ink);
  background: transparent;
}

[data-testid="stButton"] button[kind="primary"] {
  min-height: 42px;
  font-weight: 700;
}

[data-testid="stMetricValue"] {
  letter-spacing: -.035em;
}

[data-testid="stDataFrame"] {
  border-top: 1px solid var(--rr-ink);
}

.st-key-primary_action button,
.st-key-open_reviewer button {
  width: 100%;
}

@media (max-width: 800px) {
  [data-testid="stMain"] .block-container { padding-inline: 1rem; }
  .product-context, .rr-page-head, .rr-profile-head { align-items: flex-start; }
  .rr-page-head, .rr-profile-head { flex-direction: column; }
  .rr-badges { justify-content: flex-start; }
  .rr-brief { grid-template-columns: 1fr; gap: 1rem; }
  .rr-metric-strip { grid-template-columns: 1fr 1fr; }
  .rr-strip-item:nth-child(3) { border-left: 0; padding-left: 0; }
  .rr-queue-row { grid-template-columns: 34px minmax(150px, 1fr) 95px 50px; }
  .rr-queue-row > *:nth-child(4),
  .rr-queue-row > *:nth-child(5) { display: none; }
  .rr-change-row { grid-template-columns: 120px 70px 1fr 70px; }
  .rr-change-delta { grid-column: 2 / -1; }
  .rr-brief-note { padding-left: 0; padding-top: .8rem; border-left: 0; border-top: 2px solid var(--rr-primary); }
  .rr-roadmap { grid-template-columns: 1fr; }
  .rr-roadmap--head { display: none; }
  .rr-action-rail { padding-left: 0; padding-top: 1rem; border-left: 0; border-top: 1px solid var(--rr-ink); }
  .rr-profile-identity { flex-wrap: wrap; }
  .rr-profile-head { grid-template-columns: 1fr; }
  .rr-profile-meta { text-align: left; }
  .rr-policy-top { grid-template-columns: 1fr 90px; }
  .rr-flow { grid-template-columns: 1fr 30px 1fr 30px 1fr; }
}
</style>
"""


def bootstrap() -> None:
    st.set_page_config(
        page_title="Reviewer Retention",
        page_icon=":material/insights:",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={
            "About": (
                "Yelp 파워 리뷰어의 활동 변화를 바탕으로 운영 우선순위와 "
                "리텐션 개입 판단을 지원하는 프로토타입입니다."
            )
        },
    )
    st.html(CSS)
