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
  max-width: 1640px;
  padding-top: .35rem;
  padding-inline: clamp(1.4rem, 3vw, 3.2rem);
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
  font-size: .9rem;
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
  font-size: 1.28rem;
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
  grid-template-columns: 40px minmax(135px, .7fr) 88px minmax(150px, .95fr) minmax(135px, .8fr) minmax(145px, .8fr) 24px;
  align-items: center;
  gap: .75rem;
  min-height: 58px;
  padding: .55rem .35rem;
  border-bottom: 1px solid var(--rr-line);
  color: var(--rr-ink);
  font-size: .8rem;
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
.rr-state {
  display: inline-flex;
  width: fit-content;
  padding: .18rem .42rem;
  border-radius: 4px;
  font-size: .68rem;
  font-weight: 750;
}
.rr-state--retained { color: var(--rr-primary); background: #E3F1EA; }
.rr-state--weakened { color: var(--rr-focus); background: #FAEFD9; }
.rr-state--stopped { color: var(--rr-critical); background: #F7E8E5; }

.rr-score-lanes {
  display: grid;
  gap: 3px;
}
.rr-score-lanes i {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  align-items: center;
  height: 5px;
  background: #E4E9E6;
  font-style: normal;
}
.rr-score-lanes small {
  color: var(--rr-muted);
  font-size: .52rem;
  transform: translateX(-1px);
}
.rr-score-lanes b,
.rr-profile-scores b {
  display: block;
  height: 100%;
  min-width: 2px;
}
.rr-score-lanes .is-retained,
.rr-profile-scores .is-retained { background: var(--rr-primary); }
.rr-score-lanes .is-weakened,
.rr-profile-scores .is-weakened { background: #D48A43; }
.rr-score-lanes .is-stopped,
.rr-profile-scores .is-stopped { background: var(--rr-critical); }

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
.rr-policy-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .45rem;
  margin: .55rem 0;
  color: var(--rr-muted);
  font-size: .64rem;
}

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

.rr-svg-icon {
  width: 21px;
  height: 21px;
  display: block;
}

.rr-change-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.rr-change-tile {
  background: var(--rr-soft);
  border-radius: 10px;
  padding: .7rem .85rem;
}
.rr-change-tile-label {
  display: flex; align-items: center; gap: .4rem;
  color: var(--rr-muted); font-size: .68rem; margin-bottom: .4rem;
}
.rr-change-tile-label .rr-svg-icon { width: 15px; height: 15px; }
.rr-change-tile-values {
  display: flex; align-items: baseline; gap: .4rem; font-size: .78rem;
}
.rr-change-tile-values s { color: var(--rr-muted); text-decoration: line-through; }
.rr-change-tile-values strong { font-size: .95rem; }
.rr-change-tile-delta { font-size: .7rem; font-weight: 700; margin-top: .3rem; color: var(--rr-critical); }
.rr-change-tile-delta.is-positive { color: var(--rr-primary); }

.rr-flow {
  display: grid;
  grid-template-columns: 1fr 34px 1fr 34px 1fr 34px 1fr 34px 1fr;
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

.rr-decision-band {
  display: grid;
  grid-template-columns: repeat(3, minmax(0,1fr));
  border-top: 1px solid var(--rr-ink);
  border-bottom: 1px solid var(--rr-line);
}
.rr-decision-cell {
  display: grid;
  grid-template-columns: 30px 1fr;
  gap: .18rem .7rem;
  align-content: start;
  padding: 1.15rem;
}
.rr-decision-cell + .rr-decision-cell { border-left: 1px solid var(--rr-line); }
.rr-decision-cell b {
  grid-row: 1 / 4; width: 28px; height: 28px; border-radius: 50%;
  display: grid; place-items: center; background: var(--rr-primary); color: white;
}
.rr-decision-cell small,.rr-decision-cell span { color: var(--rr-muted); font-size: .66rem; }
.rr-decision-cell strong { font-size: .9rem; }

.rr-capability-grid {
  display: grid;
  grid-template-columns: repeat(4,minmax(0,1fr));
  border-top: 1px solid var(--rr-ink);
  border-bottom: 1px solid var(--rr-line);
}
.rr-capability {
  min-height: 128px;
  padding: 1rem;
}
.rr-capability + .rr-capability { border-left: 1px solid var(--rr-line); }
.rr-capability > strong { display: block; margin-top: .7rem; font-size: .88rem; }
.rr-capability p { color: var(--rr-muted); font-size: .68rem; line-height: 1.55; }

.rr-timeline-band {
  display: grid;
  grid-template-columns: repeat(3,minmax(0,1fr));
  border-top: 1px solid var(--rr-ink);
  border-bottom: 1px solid var(--rr-line);
}
.rr-time-point {
  position: relative;
  display: grid;
  grid-template-columns: 65px 28px 1fr;
  align-items: center;
  gap: .65rem;
  padding: 1.2rem;
}
.rr-time-point + .rr-time-point { border-left: 1px solid var(--rr-line); }
.rr-time-point > b { font-size: 1.45rem; color: var(--rr-primary); }
.rr-time-point > i {
  width: 25px;height:25px;border-radius:50%;display:grid;place-items:center;
  background:var(--rr-ink);color:white;font-style:normal;font-size:.7rem;
}
.rr-time-point strong { font-size: .82rem; }
.rr-time-point span { grid-column: 3; color: var(--rr-muted); font-size: .65rem; }

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
  background: var(--rr-soft);
  border-radius: 12px;
  padding: 1.1rem 1.25rem;
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

.rr-pill {
  display: inline-flex;
  align-items: center;
  font-size: .68rem;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--rr-soft);
  color: var(--rr-muted);
  white-space: nowrap;
}
.rr-pill--decided { background: #E3F1EA; color: var(--rr-primary); }

.rr-profile-card {
  background: #FFFFFF;
  border: 1px solid var(--rr-line);
  border-radius: 12px;
  padding: 1.1rem 1.25rem;
}

.rr-profile-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  flex-wrap: wrap;
}

.rr-profile-id {
  color: var(--rr-ink);
  font-size: 1.15rem;
  font-weight: 650;
  margin-bottom: .5rem;
}

.rr-profile-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.rr-profile-meta { text-align: right; color: var(--rr-muted); font-size: .68rem; white-space: nowrap; }
.rr-profile-meta small { display: block; margin-top: .22rem; }

.rr-score-rows {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--rr-line);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rr-score-row {
  display: grid;
  grid-template-columns: 56px 1fr 52px;
  align-items: center;
  gap: 10px;
  font-size: .72rem;
}
.rr-score-row span { color: var(--rr-muted); }
.rr-score-row i {
  display: block;
  height: 6px;
  border-radius: 3px;
  background: var(--rr-soft);
  font-style: normal;
  overflow: hidden;
}
.rr-score-row i b { display: block; height: 100%; border-radius: 3px; }
.rr-score-row .is-retained { background: var(--rr-primary); }
.rr-score-row .is-weakened { background: #D48A43; }
.rr-score-row .is-stopped { background: var(--rr-critical); }
.rr-score-row strong { text-align: right; }
.rr-score-note { font-size: .62rem; color: var(--rr-muted); margin-top: .5rem; }

.rr-decision-note {
  padding-top: .6rem;
  margin-top: .6rem;
  color: var(--rr-muted);
  font-size: .68rem;
  line-height: 1.55;
  border-top: 1px solid var(--rr-line);
}

.rr-evidence-card {
  background: #FFFFFF;
  border: 1px solid var(--rr-line);
  border-radius: 12px;
  padding: .25rem 1rem;
}
.rr-evidence {
  display: flex;
  gap: .7rem;
  padding: .75rem 0;
  border-bottom: 1px solid var(--rr-line);
}
.rr-evidence:last-child { border-bottom: none; }
.rr-evidence > strong {
  width: 20px; height: 20px; flex: 0 0 auto; margin-top: 1px;
  border-radius: 50%; font-weight: 600;
  display: grid; place-items: center; font-size: .64rem; color: var(--rr-muted); background: var(--rr-soft);
}
.rr-evidence > div { min-width: 0; }
.rr-evidence-title { display: block; font-size: .8rem; font-weight: 500; color: var(--rr-ink); }
.rr-evidence p { color: var(--rr-muted); font-size: .72rem; margin: .15rem 0 4px; }

.rr-chart-card {
  background: #FFFFFF;
  border: 1px solid var(--rr-line);
  border-radius: 12px;
  padding: .8rem 1rem 0;
}

.rr-action-card {
  background: #FFFFFF;
  border: 1px solid var(--rr-line);
  border-radius: 12px;
  padding: 1.1rem 1.25rem;
}
.rr-action-card h2 {
  font-size: 1.05rem;
  font-weight: 600;
  margin: .3rem 0 .35rem;
}
.rr-action-step {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: .6rem 0;
  border-top: 1px solid var(--rr-line);
}
.rr-action-step small { display: block; color: var(--rr-muted); font-size: .7rem; }
.rr-action-step strong { display: block; font-size: .78rem; font-weight: 500; text-align: right; }

.st-key-rr_decision_panel {
  background: #FFFFFF;
  border: 1px solid var(--rr-line);
  border-radius: 12px;
  padding: 1.1rem 1.25rem;
}
.st-key-rr_decision_panel .rr-section:first-child { margin-top: 0; }

.st-key-rr_nav_bar,
.st-key-rr_chart_activity,
.st-key-rr_chart_interval {
  background: #FFFFFF;
  border: 1px solid var(--rr-line);
  border-radius: 12px;
  padding: .5rem 1rem;
}
.st-key-rr_chart_activity,
.st-key-rr_chart_interval { padding: .9rem 1rem; }
.st-key-rr_chart_activity .rr-section:first-child,
.st-key-rr_chart_interval .rr-section:first-child { margin-top: 0; }
.st-key-rr_nav_bar [data-testid="stCaptionContainer"] { text-align: center; }

.st-key-rr_decision_radio .stElementContainer,
.st-key-rr_decision_radio [data-testid="stRadio"],
.st-key-rr_decision_radio [data-testid="stRadioGroup"] {
  width: 100%;
}
.st-key-rr_decision_radio [data-testid="stRadio"] label {
  border: 1px solid var(--rr-line);
  border-radius: 8px;
  padding: .5rem .65rem;
  margin-bottom: 6px;
  width: 100%;
}
.st-key-rr_decision_radio [data-testid="stRadio"] label:has(input:checked) {
  border-color: var(--rr-primary);
  background: #E3F1EA;
}

.rr-future-module {
  margin-top: .9rem;
  padding: .9rem 1rem;
  border-radius: 10px;
  background: var(--rr-soft);
}
.rr-future-module > div {
  display: flex; align-items: center; gap: .6rem;
}
.rr-future-module > div > span { color: var(--rr-muted); flex: 0 0 auto; }
.rr-future-module p { margin: .1rem 0 .45rem; color: var(--rr-muted); font-size: .65rem; }
.rr-future-module > small {
  display: flex; align-items: center; gap: .3rem; margin-top: .65rem; padding-top: .55rem;
  border-top: 1px solid var(--rr-line); color: var(--rr-muted); font-size: .6rem;
}
.rr-future-module > small .rr-svg-icon { width: 14px; height: 14px; }

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

@media (max-width: 1350px) {
  [data-testid="stMain"] .block-container { padding-inline: 1.5rem; }
  .product-brand { min-width: 190px; }
  .st-key-product_header [data-testid="stPageLink"] a {
    padding-inline: .55rem;
    font-size: .7rem;
  }
  .product-mode { gap: .35rem; }
  .product-mode span:last-child { display: none; }
  .rr-profile-meta { max-width: 220px; }
}

@media (max-width: 800px) {
  [data-testid="stMain"] .block-container { padding-inline: 1rem; }
  .product-context, .rr-page-head, .rr-profile-head { align-items: flex-start; }
  .rr-page-head, .rr-profile-head { flex-direction: column; }
  .rr-badges { justify-content: flex-start; }
  .rr-brief { grid-template-columns: 1fr; gap: 1rem; }
  .rr-metric-strip { grid-template-columns: 1fr 1fr; }
  .rr-strip-item:nth-child(3) { border-left: 0; padding-left: 0; }
  .rr-queue-row { grid-template-columns: 34px minmax(130px, 1fr) 85px 24px; }
  .rr-queue-row > *:nth-child(4),
  .rr-queue-row > *:nth-child(5),
  .rr-queue-row > *:nth-child(6) { display: none; }
  .rr-brief-note { padding-left: 0; padding-top: .8rem; border-left: 0; border-top: 2px solid var(--rr-primary); }
  .rr-roadmap { grid-template-columns: 1fr; }
  .rr-roadmap--head { display: none; }
  .rr-profile-meta { text-align: left; }
  .rr-policy-top { grid-template-columns: 1fr 90px; }
  .rr-flow {
    grid-template-columns: 1fr;
    gap: .45rem;
  }
  .rr-flow > i {
    width: 1px;
    height: 18px;
    margin: 0 auto;
  }
  .rr-capability-grid { grid-template-columns: 1fr 1fr; }
  .rr-capability:nth-child(3) { border-left: 0; border-top: 1px solid var(--rr-line); }
  .rr-capability:nth-child(4) { border-top: 1px solid var(--rr-line); }
  .rr-decision-band,.rr-timeline-band { grid-template-columns: 1fr; }
  .rr-decision-cell + .rr-decision-cell,.rr-time-point + .rr-time-point {
    border-left: 0; border-top: 1px solid var(--rr-line);
  }
}

.rr-hero-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.2rem;
  padding: 1.3rem .1rem 0;
}

.rr-hero-badge-col { text-align: right; }
.rr-hero-badge-col .rr-snapshot-note {
  font-size: .68rem; color: var(--rr-muted); margin-top: 6px;
}

.rr-card {
  background: #FFFFFF;
  border: 1px solid var(--rr-line);
  border-radius: 12px;
}

.rr-qhead {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: .55rem;
}
.rr-qhead strong { font-size: .92rem; font-weight: 650; }
.rr-qhead span { font-size: .74rem; color: var(--rr-muted); }

.rr-qrow {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: .92rem 1rem;
  border-bottom: 1px solid var(--rr-line);
  text-decoration: none;
  color: var(--rr-ink);
}
.rr-qrow:last-child { border-bottom: none; }
.rr-qrow:hover { background: #F6F8F6; }

.rr-qrank {
  width: 24px; height: 24px; flex: 0 0 auto;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: .68rem; font-weight: 700; color: #fff;
}
.rr-qrank--stopped-strong { background: var(--rr-critical); }
.rr-qrank--stopped-soft { background: #E8A39A; }
.rr-qrank--weakened-strong { background: var(--rr-focus); }
.rr-qrank--weakened-soft { background: #D9AE72; }
.rr-qrank--retained-strong { background: var(--rr-primary); }
.rr-qrank--retained-soft { background: var(--rr-primary-alt); }

.rr-qname { font-size: .86rem; font-weight: 600; flex: 1; min-width: 0; }
.rr-qchange { font-size: .78rem; color: var(--rr-muted); flex: 1.6; }
.rr-qaction { font-size: .78rem; color: var(--rr-ink); flex: 1.3; }
.rr-qarrow { color: var(--rr-muted); font-style: normal; }

.rr-policy-card { padding: 1.1rem 1.25rem; }
.rr-policy-card h3 { font-size: .88rem; font-weight: 650; margin: 0 0 2px; }
.rr-policy-card .rr-policy-sub { font-size: .72rem; color: var(--rr-muted); margin: 0 0 .8rem; }

.rr-policy-row {
  display: flex; align-items: baseline; justify-content: space-between;
  padding: .55rem 0; border-top: 1px solid var(--rr-line);
}
.rr-policy-row .rr-p-label { font-size: .78rem; color: var(--rr-muted); }
.rr-policy-row .rr-p-value { font-size: 1.05rem; font-weight: 600; }
.rr-policy-row .rr-p-value.is-good { color: var(--rr-primary); }

.rr-policy-caption { font-size: .68rem; color: var(--rr-muted); margin: 2px 0 0; }

.rr-lift-row { padding: .55rem 0 2px; border-top: 1px solid var(--rr-line); margin-bottom: .85rem; }
.rr-lift-top {
  display: flex; align-items: baseline; justify-content: space-between;
  margin-bottom: .4rem; font-size: .72rem; color: var(--rr-muted);
}
.rr-lift-top .rr-p-value { font-size: .85rem; color: var(--rr-primary); font-weight: 600; }
.rr-lift-track { position: relative; height: 4px; border-radius: 2px; background: var(--rr-soft); }
.rr-lift-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 2px; background: var(--rr-primary); }
.rr-lift-marker { position: absolute; left: 50%; top: -2px; bottom: -2px; width: 2px; background: #B8C0BB; }

.rr-policy-split {
  display: flex; justify-content: space-between;
  font-size: .72rem; color: var(--rr-muted);
  border-top: 1px solid var(--rr-line); padding-top: .55rem;
}

.rr-qrank-plain {
  font-size: .68rem; padding: 3px 10px; border-radius: 999px;
  background: var(--rr-soft); color: var(--rr-muted); flex: 0 0 auto;
  white-space: nowrap; justify-self: start;
}

.rr-qaction-badge {
  font-size: .72rem; padding: 3px 10px; border-radius: 4px;
  background: var(--rr-soft); color: var(--rr-muted); flex: 0 0 auto;
  white-space: nowrap;
}
.rr-qaction-badge--done { background: var(--rr-primary); color: #FFFFFF; }

.rr-qsignal-tag {
  font-size: .68rem; padding: 2px 8px; border-radius: 4px;
  background: var(--rr-soft); color: var(--rr-muted);
  white-space: nowrap;
}

.rr-worklist-card { max-width: 1180px; }
.rr-worklist-scroll { overflow-x: auto; }
.rr-wrow-head, .rr-wrow {
  display: grid;
  grid-template-columns: 46px 150px 84px minmax(200px, 1fr) 116px 150px 20px;
  gap: 10px;
  align-items: center;
}
.rr-worklist-scroll .rr-wrow-head, .rr-worklist-scroll .rr-wrow { min-width: 820px; }
.rr-wrow-head {
  padding: .5rem 1rem;
  font-size: .66rem;
  font-weight: 600;
  color: var(--rr-muted);
  border-bottom: 1px solid var(--rr-line);
}
.rr-wrow {
  padding: .78rem 1rem;
  border-bottom: 1px solid var(--rr-line);
  text-decoration: none;
  color: var(--rr-ink);
}
.rr-wrow:last-child { border-bottom: none; }
.rr-wrow:hover { background: #F6F8F6; }
.rr-wrow--done {
  border-left: 3px solid var(--rr-primary);
  padding-left: calc(1rem - 3px);
  background: rgba(19, 122, 90, .04);
}
.rr-wrow--done:hover { background: rgba(19, 122, 90, .07); }
.rr-wrow-head > *, .rr-wrow > * { justify-self: start; min-width: 0; }
.rr-wname {
  font-size: .78rem; font-weight: 500; color: var(--rr-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}
.rr-wmetric {
  font-size: .78rem; color: var(--rr-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}

.rr-stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  max-width: 1180px;
  margin-bottom: 1rem;
}
.rr-stat-card { padding: .7rem 1rem; }
.rr-stat-label { font-size: .72rem; color: var(--rr-muted); }
.rr-stat-value { font-size: 1.25rem; font-weight: 650; margin-top: 2px; }
.rr-stat-value--good { color: var(--rr-primary); }

@media (max-width: 800px) {
  .rr-hero-head { flex-direction: column; }
  .rr-hero-badge-col { text-align: left; }
  .rr-qrow { flex-wrap: wrap; row-gap: .3rem; }
  .rr-qchange, .rr-qaction { flex: 1 1 100%; }
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
