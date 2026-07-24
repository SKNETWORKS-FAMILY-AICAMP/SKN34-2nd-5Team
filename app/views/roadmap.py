from __future__ import annotations

import pandas as pd
import streamlit as st

from core.components import footer, page_intro, section_header
from core.data import load_app_data


data = load_app_data()

page_intro(
    "Product readiness",
    "제품 상태와 확장 조건",
    "로드맵은 상단의 모델 신뢰·로드맵 화면에 통합되어 있습니다. 이 문서는 기능 준비도를 독립적으로 점검하기 위한 호환 화면입니다.",
    ["현재 사용 가능"],
)

section_header(
    "기능 준비도",
    "상태만 표시하지 않고 필요한 데이터와 활성화 조건을 함께 관리합니다.",
)
readiness = pd.DataFrame(
    [
        ["운영 홈·검토 큐", "현재 사용 가능", "위험 프로필 결과", "연결 완료"],
        [
            "위험 유형 플레이북",
            "규칙 기반 프로토타입",
            "규칙 검증·운영 피드백",
            "운영 검토",
        ],
        [
            "월별 활동 타임라인",
            "데이터 연결 필요",
            "reviewer_monthly_activity_v01.parquet",
            "계약 검증",
        ],
        [
            "지역 콘텐츠 위험",
            "정의·데이터 필요",
            "지역 정의·최소 표본·집계",
            "기준 확정",
        ],
        [
            "캠페인 성과 추적",
            "외부 연동 필요",
            "CRM 발송·참여·복귀 이벤트",
            "외부 계약",
        ],
        [
            "개인별 SHAP·보정 확률",
            "분석 검증 필요",
            "설명 안정성·Calibration",
            "분석 검증",
        ],
    ],
    columns=["기능", "현재 상태", "필요 데이터·검증", "활성화 조건"],
)
st.dataframe(readiness, hide_index=True, width="stretch")
st.info(
    "실제 구현에서는 모델 신뢰 센터의 `제품 상태·로드맵` 보기에서 같은 내용을 확인합니다.",
    icon=":material/info:",
)

footer(data.data_mode)
