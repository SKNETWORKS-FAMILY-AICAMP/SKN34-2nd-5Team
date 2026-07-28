from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from core.charts import (
    confusion_heatmap,
    feature_importance,
    group_importance,
    model_comparison,
    multiclass_class_performance,
    multiclass_top_k_curve,
    top_k_curve,
)
from core.components import (
    capability_grid,
    empty_state,
    footer,
    metric_strip,
    page_intro,
    render_warnings,
    section_header,
    status_badge,
    timeline_band,
)
from core.data import load_app_data


data = load_app_data()

page_intro(
    "Model trust & product readiness",
    "모델을 어디까지 믿고 사용할지 보여줍니다",
    "성능, 시간 분할, 피처 근거와 제품 준비도를 운영 관점에서 공개합니다.",
    ["현재 데모에서 사용 가능" if data.data_mode == "demo" else "현재 사용 가능"],
)

view = st.segmented_control(
    "신뢰 센터 보기",
    ["성능과 Top-K", "시간 분할·누수 방지", "피처 근거", "제품 상태·로드맵"],
    default="성능과 Top-K",
    key="trust_view",
    width="stretch",
)

if view == "성능과 Top-K":
    multiclass_validation = data.multiclass_validation
    if multiclass_validation.empty:
        empty_state(
            "Test 성능",
            f"{data.model_version} 검증 결과 파일이 연결되면 3클래스 성능을 표시합니다.",
            "데이터 연결 필요",
        )
    else:
        final_row = multiclass_validation.loc[
            multiclass_validation["record_type"].eq("final_test")
        ].iloc[0]
        section_header(
            f"{data.model_version} 3클래스 모델 성능",
            (
                f"비교 {data.comparison_year} · 선정·피처 마감 "
                f"{data.selection_year} · 실제 상태 검증 {data.target_year} 결과입니다."
            ),
            "현재 사용 가능",
        )
        metric_strip(
            [
                ("Macro F1", f"{float(final_row['macro_f1']):.3f}", "3클래스 평균 F1"),
                ("Macro PR-AUC", f"{float(final_row['macro_pr_auc']):.3f}", "불균형 데이터 핵심 지표"),
                ("Macro ROC-AUC", f"{float(final_row['macro_ovr_roc_auc']):.3f}", "전체 순위 구분 성능"),
                (
                    "Balanced Accuracy",
                    f"{float(final_row['balanced_accuracy']):.1%}",
                    "클래스 불균형 보정 정확도",
                ),
            ]
        )
        st.plotly_chart(
            multiclass_class_performance(multiclass_validation),
            width="stretch",
            key="trust_class_performance",
        )
        if not data.multiclass_confusion.empty:
            st.plotly_chart(
                confusion_heatmap(data.multiclass_confusion),
                width="stretch",
                key="trust_confusion_heatmap",
            )

    section_header(
        "통합 상위 20% 운영 성과",
        "약화·중단 점수를 합산한 통합 우선순위의 사후 Test 검증 결과입니다.",
        "현재 사용 가능",
    )
    if data.multiclass_top_k.empty:
        empty_state(
            "통합 Top-K 성능",
            f"{data.model_version} Top-K 결과 파일이 연결되면 정책별 Recall과 Lift를 표시합니다.",
            "데이터 연결 필요",
        )
    else:
        st.plotly_chart(
            multiclass_top_k_curve(data.multiclass_top_k),
            width="stretch",
            key="trust_top_k_curve",
        )
        unified = data.multiclass_top_k.loc[
            data.multiclass_top_k["split"].eq("final_test")
            & data.multiclass_top_k["ranking"].eq("unified")
        ].sort_values("target_rate")
        top_k_table = unified.rename(
            columns={
                "target_rate": "검토 비율",
                "target_users": "검토 인원",
                "status_loss_captured": "포착 지위상실",
                "status_loss_precision": "Precision",
                "status_loss_recall": "Recall",
                "status_loss_lift": "Lift",
                "stopped_captured": "중단 포착",
                "stopped_recall": "중단 Recall",
                "weakened_captured": "약화 포착",
                "weakened_recall": "약화 Recall",
            }
        )[
            [
                "검토 비율", "검토 인원", "포착 지위상실", "Precision", "Recall", "Lift",
                "중단 포착", "중단 Recall", "약화 포착", "약화 Recall",
            ]
        ]
        st.dataframe(
            top_k_table,
            hide_index=True,
            width="stretch",
            column_config={
                "검토 비율": st.column_config.NumberColumn(format="percent"),
                "Precision": st.column_config.NumberColumn(format="percent"),
                "Recall": st.column_config.NumberColumn(format="percent"),
                "Lift": st.column_config.NumberColumn(format="%.2f×"),
                "중단 Recall": st.column_config.NumberColumn(format="percent"),
                "약화 Recall": st.column_config.NumberColumn(format="percent"),
            },
        )

    if not data.multiclass_validation_v03.empty:
        with st.expander(
            "v03 비교 기준 (3클래스 이전 코호트, 참고용)",
            expanded=False,
            icon=":material/history:",
        ):
            st.caption(
                "v03은 2017년 후보 선정 → 2018년 활동 관찰 → 2019년 실제 상태 "
                "검증 구조를 사용한 이전 3클래스 모델입니다. "
                f"{data.model_version} 운영 화면의 기본 수치로 혼합하지 않습니다."
            )
            v03_final = data.multiclass_validation_v03.loc[
                data.multiclass_validation_v03["record_type"].eq("final_test")
            ].iloc[0]
            metric_strip(
                [
                    (
                        "Macro F1",
                        f"{float(v03_final['macro_f1']):.3f}",
                        "v03 Test · 3클래스 평균 F1",
                    ),
                    (
                        "Macro PR-AUC",
                        f"{float(v03_final['macro_pr_auc']):.3f}",
                        "v03 Test · 불균형 데이터 핵심 지표",
                    ),
                    (
                        "Macro ROC-AUC",
                        f"{float(v03_final['macro_ovr_roc_auc']):.3f}",
                        "v03 Test · 전체 순위 구분 성능",
                    ),
                    (
                        "Test 표본",
                        f"{int(v03_final['validation_samples']):,}명",
                        "v03 이전 코호트",
                    ),
                ]
            )
            st.plotly_chart(
                multiclass_class_performance(data.multiclass_validation_v03),
                width="stretch",
                key="trust_class_performance_v03",
            )
            if not data.multiclass_confusion_v03.empty:
                st.plotly_chart(
                    confusion_heatmap(data.multiclass_confusion_v03),
                    width="stretch",
                    key="trust_confusion_heatmap_v03",
                    config={"displayModeBar": False, "responsive": True},
                )
            if not data.multiclass_top_k_v03.empty:
                st.plotly_chart(
                    multiclass_top_k_curve(data.multiclass_top_k_v03),
                    width="stretch",
                    key="trust_top_k_curve_v03",
                )
                v03_top20 = data.multiclass_top_k_v03.loc[
                    data.multiclass_top_k_v03["split"].eq("final_test")
                    & data.multiclass_top_k_v03["ranking"].eq("unified")
                    & data.multiclass_top_k_v03["target_rate"].eq(0.20)
                ].iloc[0]
                metric_strip(
                    [
                        ("상위 20%", f"{int(v03_top20['target_users']):,}명", "v03 검토 인원"),
                        (
                            "지위 상실 포착",
                            f"{int(v03_top20['status_loss_captured']):,}명",
                            "약화·중단 실제 결과",
                        ),
                        (
                            "Precision",
                            f"{float(v03_top20['status_loss_precision']):.2%}",
                            "v03 상위 20%",
                        ),
                        (
                            "Recall",
                            f"{float(v03_top20['status_loss_recall']):.2%}",
                            "v03 상위 20%",
                        ),
                        (
                            "Lift",
                            f"{float(v03_top20['status_loss_lift']):.2f}배",
                            "v03 무작위 대비",
                        ),
                    ]
                )

    with st.expander(
        "v02 비교 기준 (이진 이탈 모델, 참고용)",
        expanded=False,
        icon=":material/history:",
    ):
        st.caption(
            "v02는 완전 이탈(churn)만을 이진 분류한 이전 세대 모델입니다. "
            f"{data.model_version} 운영 화면의 기본 수치로 혼합하지 않습니다."
        )
        validation_test = data.validation_test
        if not validation_test.empty:
            test = validation_test.loc[
                validation_test["dataset"].astype(str).str.lower().eq("test")
            ]
            metric_source = test.iloc[0] if not test.empty else validation_test.iloc[-1]
            metric_specs = [
                ("PR-AUC", "pr_auc", "불균형 데이터 핵심 지표"),
                ("ROC-AUC", "roc_auc", "전체 순위 구분 성능"),
                ("Recall", "recall", "전체 이탈자 포착률"),
                ("Precision", "precision", "선별 대상 내 실제 이탈"),
            ]
            metric_strip(
                [
                    (
                        label,
                        (
                            f"{float(metric_source.get(field, 0.0)):.3f}"
                            if "AUC" in label
                            else f"{float(metric_source.get(field, 0.0)):.1%}"
                        ),
                        f"v02 Test · {note}",
                    )
                    for label, field, note in metric_specs
                ]
            )
            st.plotly_chart(
                model_comparison(validation_test),
                width="stretch",
                key="trust_model_comparison_v02",
            )
        if not data.top_k.empty:
            st.plotly_chart(
                top_k_curve(data.top_k),
                width="stretch",
                key="trust_top_k_curve_v02",
            )
            top_k_table_v02 = data.top_k.copy().rename(
                columns={
                    "target_rate_pct": "검토 비율",
                    "target_users": "검토 인원",
                    "captured_churn_users": "포착 이탈자",
                    "precision_at_k": "Precision@K",
                    "recall_at_k": "Recall@K",
                    "lift_at_k": "Lift@K",
                    "minimum_risk_score": "최소 점수",
                }
            )
            st.dataframe(
                top_k_table_v02,
                hide_index=True,
                width="stretch",
                column_config={
                    "검토 비율": st.column_config.NumberColumn(format="%d%%"),
                    "Precision@K": st.column_config.NumberColumn(format="percent"),
                    "Recall@K": st.column_config.NumberColumn(format="percent"),
                    "Lift@K": st.column_config.NumberColumn(format="%.2f×"),
                    "최소 점수": st.column_config.NumberColumn(format="%.4f"),
                },
            )

elif view == "시간 분할·누수 방지":
    section_header(
        "시간 순서를 지키는 평가 구조",
        "운영 시점에 알 수 없는 미래 정보를 피처에 포함하지 않습니다.",
        "현재 사용 가능",
    )
    timeline_specs = [
        (str(data.comparison_year), "비교 연도", "이전 활동 패턴 비교"),
        (
            str(data.selection_year),
            "후보 선정·피처 마감",
            "파워 리뷰어 선정과 모델 입력 생성",
        ),
        (str(data.target_year), "실제 상태 검증", "유지·약화·중단 결과 확인"),
    ]
    timeline_band(timeline_specs)

    section_header("누수 방지와 해석 원칙")
    capability_grid(
        [
            ("미래 정보 제외", "검증 연도의 리뷰 활동은 피처에 포함하지 않습니다.", "현재 사용 가능"),
            ("정답 분리", "실제 결과는 운영 기본 화면에서 숨깁니다.", "현재 사용 가능"),
            ("순위 점수", "위험 점수를 이탈 확률로 해석하지 않습니다.", "현재 사용 가능"),
            ("추론 제한", "거주지·직장·실제 생활 변화를 추론하지 않습니다.", "현재 사용 가능"),
        ]
    )

elif view == "피처 근거":
    is_v04_importance = "v04" in data.sources.get("feature_importance", "")
    feature_column, group_column = st.columns([1.2, 0.8], gap="large")
    with feature_column:
        section_header(
            "피처 중요도" + (f" · {data.model_version}" if is_v04_importance else ""),
            (
                f"최종 Test {int(data.model_metadata.get('test_samples', len(data.reviewer_profiles))):,}명 · "
                "단일 피처 Permutation 20회 · "
                "Macro PR-AUC 감소량입니다."
            ),
            "현재 사용 가능" if not data.feature_importance.empty else "데이터 연결 필요",
        )
        if data.feature_importance.empty:
            empty_state(
                "피처 중요도",
                "검증된 중요도 결과 파일을 연결해야 표시할 수 있습니다.",
                "데이터 연결 필요",
            )
        else:
            st.plotly_chart(
                feature_importance(data.feature_importance),
                width="stretch",
                key="trust_feature_importance",
            )
    with group_column:
        section_header(
            "피처 그룹" + (f" · {data.model_version}" if is_v04_importance else ""),
            (
                "그룹 내부 관계를 유지한 공동 Permutation 20회 결과입니다. "
                "활동량·작성 간격·탐색을 비교합니다."
            ),
            "현재 사용 가능" if not data.group_importance.empty else "데이터 연결 필요",
        )
        if data.group_importance.empty:
            empty_state(
                "피처 그룹 중요도",
                "그룹 중요도 결과 파일을 연결해야 표시할 수 있습니다.",
                "데이터 연결 필요",
            )
        else:
            st.plotly_chart(
                group_importance(data.group_importance),
                width="stretch",
                key="trust_group_importance",
            )

    st.caption(
        "중요도는 모델 선정이 아닌 사후 해석 전용입니다. 값은 확률이나 "
        "영향 비율이 아니라 정보를 섞었을 때 감소한 Macro PR-AUC입니다. "
        f"기준 Macro PR-AUC {float(data.model_metadata.get('test_metrics', {}).get('macro_pr_auc', 0)):.4f}"
    )

    if is_v04_importance and not data.group_importance_v03.empty:
        with st.expander(
            "v03 비교 기준 (3클래스 이전 코호트, 참고용)",
            expanded=False,
            icon=":material/history:",
        ):
            st.caption(
                "v03 최종 Test 4,157명의 Permutation 중요도입니다. "
                "기준 Macro PR-AUC는 0.5986이며, v04 기본 중요도와 혼합하지 않는 "
                "이전 코호트 비교 자료입니다."
            )
            v03_feature_column, v03_group_column = st.columns(
                [1.2, 0.8],
                gap="large",
            )
            with v03_feature_column:
                st.plotly_chart(
                    feature_importance(data.feature_importance_v03),
                    width="stretch",
                    key="trust_feature_importance_v03",
                )
            with v03_group_column:
                st.plotly_chart(
                    group_importance(data.group_importance_v03),
                    width="stretch",
                    key="trust_group_importance_v03",
                )

    if is_v04_importance and not data.group_importance_v02.empty:
        with st.expander(
            "v02 비교 기준 (이진 이탈 모델, 참고용)",
            expanded=False,
            icon=":material/history:",
        ):
            st.caption(
                "v02는 완전 이탈만 예측하는 이전 세대 모델의 중요도입니다. "
                f"{data.model_version} 기본 중요도와 혼합하지 않는 과거 비교 자료입니다."
            )
            v02_feature_column, v02_group_column = st.columns([1.2, 0.8], gap="large")
            with v02_feature_column:
                if not data.feature_importance_v02.empty:
                    st.plotly_chart(
                        feature_importance(data.feature_importance_v02),
                        width="stretch",
                        key="trust_feature_importance_v02",
                    )
            with v02_group_column:
                st.plotly_chart(
                    group_importance(data.group_importance_v02),
                    width="stretch",
                    key="trust_group_importance_v02",
                )

    section_header(
        "개인별 설명 범위",
        "현재 운영 화면과 향후 분석 기능을 구분합니다.",
    )
    scope = pd.DataFrame(
        [
            ["행동 변화 비교", "현재 사용 가능", "프로필 집계 컬럼"],
            ["규칙 기반 위험 근거", "규칙 기반 프로토타입", "설명 규칙 검증 필요"],
            ["개인별 SHAP", "분석 검증 필요", "설명 안정성 검증 필요"],
            ["보정된 이탈 확률", "현재 제외", "Calibration 필요"],
        ],
        columns=["설명 기능", "상태", "조건"],
    )
    st.dataframe(scope, hide_index=True, width="stretch")

else:
    section_header(
        "제품 상태와 확장 조건",
        "기능별 현재 상태, 필요한 데이터와 활성화 후 가치를 공개합니다.",
    )
    roadmap = [
        (
            "운영 홈·검토 큐",
            "현재 사용 가능",
            "위험 프로필 결과",
            "우선 검토 대상 발견",
        ),
        (
            "위험 유형 플레이북",
            "규칙 기반 프로토타입",
            "규칙 검증·운영 피드백",
            "일관된 개입 판단",
        ),
        (
            "월별 활동 타임라인",
            "데이터 연결 필요",
            "월별 리뷰 활동 파일",
            "감소 시점·회복 확인",
        ),
        (
            "지역 콘텐츠 위험",
            "정의·데이터 필요",
            "지역 정의·최소 표본·집계",
            "지역별 콘텐츠 공급 대응",
        ),
        (
            "캠페인 성과 추적",
            "외부 연동 필요",
            "CRM 발송·참여·복귀 데이터",
            "개입 효과 비교",
        ),
        (
            "개인별 SHAP·보정 확률",
            "분석 검증 필요",
            "설명 안정성·Calibration",
            "세부 근거·확률 해석",
        ),
    ]
    markup = (
        '<div class="rr-roadmap rr-roadmap--head">'
        "<span>기능</span><span>현재 상태</span>"
        "<span>필요 데이터·검증</span><span>활성화 후 제공 가치</span></div>"
    )
    for feature, status, need, value in roadmap:
        markup += (
            '<div class="rr-roadmap">'
            f"<strong>{html.escape(feature)}</strong>"
            f"<span>{status_badge(status)}</span>"
            f"<span>{html.escape(need)}</span>"
            f"<span>{html.escape(value)}</span></div>"
        )
    st.html(markup)

    section_header(
        "연결된 산출물",
        "현재 앱이 실제로 읽고 있는 데이터 파일입니다.",
    )
    if data.sources:
        sources = pd.DataFrame(
            [{"데이터": key, "출처": value} for key, value in data.sources.items()]
        )
        st.dataframe(sources, hide_index=True, width="stretch")
    else:
        st.caption("연결된 프로젝트 산출물이 없습니다.")

render_warnings(data.warnings)
footer(data.data_mode)
