from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core.data import load_app_data
from core.theme import bootstrap


bootstrap()
data = load_app_data()

st.session_state.setdefault("selected_reviewer_id", None)
st.session_state.setdefault("reviewer_workspace_mode", "list")
st.session_state.setdefault("validation_mode", False)

pages = [
    st.Page(
        "views/operation_home.py",
        title="운영 홈",
        icon=":material/space_dashboard:",
        url_path="operations",
        default=True,
    ),
    st.Page(
        "views/risk_queue.py",
        title="리뷰어 관리",
        icon=":material/groups:",
        url_path="reviewers",
    ),
    st.Page(
        "views/playbook.py",
        title="리텐션 플레이북",
        icon=":material/strategy:",
        url_path="playbook",
    ),
    st.Page(
        "views/regional_risk.py",
        title="콘텐츠 위험",
        icon=":material/map:",
        url_path="regional",
    ),
    st.Page(
        "views/trust_center.py",
        title="모델 신뢰·로드맵",
        icon=":material/verified:",
        url_path="trust",
    ),
]

navigation = st.navigation(pages, position="hidden")

mode_label = {
    "project": "PROJECT",
    "hybrid": "HYBRID",
    "demo": "DEMO",
}.get(data.data_mode, str(data.data_mode).upper())

with st.container(
    key="product_header",
    horizontal=True,
    vertical_alignment="center",
    gap="xsmall",
):
    st.html(
        """
        <div class="product-brand">
          <span class="product-mark" aria-hidden="true"></span>
          <span>Reviewer Retention</span>
        </div>
        """
    )
    for page in pages:
        st.page_link(page, label=page.title, icon=page.icon)
    st.html(
        f"""
        <div class="product-mode">
          <span>{mode_label}</span>
          <span>Test · 2019</span>
        </div>
        """
    )

navigation.run()
