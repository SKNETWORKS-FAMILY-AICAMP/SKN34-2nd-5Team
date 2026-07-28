from __future__ import annotations

import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_DIR = (
    Path(__file__).resolve().parents[1]
    / "archive"
    / "app_streamlit_v04"
)
sys.path.insert(0, str(APP_DIR))

from core.data import (  # noqa: E402
    VALIDATION_ONLY_COLUMNS,
    load_app_data,
    operational_profile_export,
)
from core.charts import interval_comparison, profile_activity  # noqa: E402
from core.decisions import decision_key  # noqa: E402


class UiContractTest(unittest.TestCase):
    def _render(self, relative_path: str) -> AppTest:
        app = AppTest.from_file(
            str(APP_DIR / relative_path),
            default_timeout=45,
        ).run()
        self.assertEqual(list(app.exception), [])
        return app

    @staticmethod
    def _html(app: AppTest) -> str:
        return "\n".join(item.proto.body for item in app.get("html"))

    def test_operation_home_contains_validated_policy(self) -> None:
        app = self._render("views/operation_home.py")
        html = self._html(app)
        self.assertIn("1,307명", html)
        self.assertIn("1,142명", html)
        self.assertIn("87.4%", html)
        self.assertIn("1.45배", html)
        self.assertIn("유지 우세 2,332명", html)
        self.assertIn("약화 우세 3,038명", html)
        self.assertIn("중단 우세 1,163명", html)
        self.assertIn("이번 세션 우선 검토", html)
        self.assertIn("rr-qrow", html)
        self.assertIn("rr-policy-card", html)

    def test_risk_queue_has_operating_controls(self) -> None:
        app = self._render("views/risk_queue.py")
        self.assertEqual(len(app.text_input), 1)
        self.assertEqual(len(app.multiselect), 2)
        self.assertEqual(len(app.selectbox), 2)
        self.assertEqual(len(app.download_button), 1)
        self.assertEqual(len(app.segmented_control), 2)
        self.assertIn("rr-wrow", self._html(app))
        self.assertIn("통합 상위 20%", list(app.selectbox[0].options))

    def test_operational_download_excludes_validation_truth(self) -> None:
        data = load_app_data()
        export = operational_profile_export(
            data.reviewer_profiles,
            list(data.model_metadata["feature_columns"]),
        )
        self.assertFalse(VALIDATION_ONLY_COLUMNS & set(export.columns))
        self.assertIn("sample_id", export.columns)
        self.assertIn("user_id", export.columns)
        self.assertIn("model_version", export.columns)
        self.assertIn("priority_rank", export.columns)

    def test_priority_link_opens_detail_and_returns_to_queue(self) -> None:
        app = AppTest.from_file(
            str(APP_DIR / "views/risk_queue.py"),
            default_timeout=45,
        )
        app.query_params["reviewer"] = str(
            load_app_data().reviewer_profiles.iloc[0]["user_id"]
        )
        app.run()
        self.assertEqual(list(app.exception), [])
        self.assertIn("rr-profile-head", self._html(app))

        app.button(key="back_to_queue").click().run()
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.text_input), 1)

    def test_reviewer_360_has_decision_and_validation_controls(self) -> None:
        app = self._render("views/reviewer_360.py")
        html = self._html(app)
        self.assertIn("rr-profile-head", html)
        self.assertIn("rr-change-grid", html)
        self.assertIn("rr-svg-icon", html)
        self.assertNotIn("material-symbols-rounded", html)
        self.assertIn("왜 우선 검토 대상인가", html)
        self.assertIn("Recommended playbook", html)
        self.assertIn("rr-future-module", html)
        self.assertEqual(app.toggle[0].label, "검증 정답 표시")
        self.assertEqual(len(app.segmented_control), 1)
        self.assertEqual(len(app.radio), 1)
        self.assertTrue(
            any(button.label == "세션 판단 적용" for button in app.button)
        )

        app.toggle(key="validation_mode").set_value(True).run()
        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.segmented_control[0].value, "사후 검증")
        self.assertTrue(
            any(metric.label == "실제 상태" for metric in app.metric)
        )
        self.assertTrue(
            any(metric.label == "2019년 리뷰" for metric in app.metric)
        )

    def test_profile_charts_do_not_create_empty_plotly_titles(self) -> None:
        row = load_app_data().reviewer_profiles.iloc[0]
        for figure in (profile_activity(row), interval_comparison(row)):
            self.assertNotIn("title", figure.to_plotly_json()["layout"])

    def test_playbook_exposes_future_campaign_structure(self) -> None:
        app = self._render("views/playbook.py")
        html = self._html(app)
        self.assertIn("캠페인 실행과 성과 추적", html)
        self.assertTrue(app.button[0].disabled)

    def test_playbook_accepts_reviewer_360_context(self) -> None:
        row = load_app_data().reviewer_profiles.iloc[0]
        app = AppTest.from_file(
            str(APP_DIR / "views/playbook.py"),
            default_timeout=45,
        )
        app.session_state["playbook_context"] = {
            "sample_id": str(row["sample_id"]),
            "user_id": str(row["user_id"]),
            "manager_decision": "미검토",
            "risk_type": str(row["risk_type"]),
            "model_judgment": str(row["model_judgment"]),
            "priority_rank": int(row["priority_rank"]),
            "priority_top_percent": float(row["priority_top_percent"]),
            "priority_score": float(row["priority_score"]),
            "selected_for_crm": bool(row["crm_target"]),
        }
        app.session_state["playbook_view_mode"] = "현재 리뷰어에게 추천"
        app.run()
        self.assertEqual(list(app.exception), [])
        self.assertIn(str(row["sample_id"]), "\n".join(c.value for c in app.caption))

    def test_decision_key_isolated_by_model_and_sample(self) -> None:
        self.assertNotEqual(
            decision_key("v03", "sample-a"),
            decision_key("v04", "sample-a"),
        )
        self.assertNotEqual(
            decision_key("v04", "sample-a"),
            decision_key("v04", "sample-b"),
        )

    def test_regional_page_does_not_invent_values(self) -> None:
        app = self._render("views/regional_risk.py")
        html = self._html(app)
        self.assertIn("지역별 위험 집계 연결 대기", html)
        self.assertIn("정의·데이터 필요", html)
        self.assertEqual(len(app.metric), 0)

    def test_trust_center_has_top_k_and_roadmap_modes(self) -> None:
        app = self._render("views/trust_center.py")
        options = list(app.segmented_control[0].options)
        self.assertIn("성능과 Top-K", options)
        self.assertIn("시간 분할·누수 방지", options)
        self.assertIn("피처 근거", options)
        self.assertIn("제품 상태·로드맵", options)
        self.assertEqual(
            [(status.label, status.proto.expanded) for status in app.status],
            [
                ("v03 비교 기준 (3클래스 이전 코호트, 참고용)", False),
                ("v02 비교 기준 (이진 이탈 모델, 참고용)", False),
            ],
        )

        app.segmented_control[0].set_value("피처 근거").run()
        self.assertEqual(list(app.exception), [])
        html = self._html(app)
        self.assertIn("피처 중요도 · v04", html)
        self.assertIn("사후 해석 전용", "\n".join(c.value for c in app.caption))
        self.assertEqual(
            [(status.label, status.proto.expanded) for status in app.status],
            [
                ("v03 비교 기준 (3클래스 이전 코호트, 참고용)", False),
                ("v02 비교 기준 (이진 이탈 모델, 참고용)", False),
            ],
        )

    def test_v03_trust_comparison_bundle_is_complete_and_separate(self) -> None:
        data = load_app_data()
        final_row = data.multiclass_validation_v03.loc[
            data.multiclass_validation_v03["record_type"].eq("final_test")
        ].iloc[0]
        top20 = data.multiclass_top_k_v03.loc[
            data.multiclass_top_k_v03["split"].eq("final_test")
            & data.multiclass_top_k_v03["ranking"].eq("unified")
            & data.multiclass_top_k_v03["target_rate"].eq(0.20)
        ].iloc[0]

        self.assertEqual(int(final_row["validation_samples"]), 4_157)
        self.assertAlmostEqual(float(final_row["macro_f1"]), 0.5754081477)
        self.assertAlmostEqual(float(final_row["macro_pr_auc"]), 0.5985820399)
        self.assertEqual(int(top20["target_users"]), 832)
        self.assertEqual(int(top20["status_loss_captured"]), 773)
        self.assertEqual(len(data.feature_importance_v03), 43)
        self.assertEqual(int(data.group_importance_v03["feature_count"].sum()), 43)
        self.assertIn("v03", data.sources["multiclass_validation_v03"])
        self.assertIn("v04", data.sources["multiclass_validation"])


if __name__ == "__main__":
    unittest.main()
