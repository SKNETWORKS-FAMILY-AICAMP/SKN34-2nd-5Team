from __future__ import annotations

import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))


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
        self.assertIn("4,157명", html)
        self.assertIn("832명", html)
        self.assertIn("346명", html)
        self.assertIn("2.58×", html)
        self.assertIn("우선 검토 큐", html)
        self.assertIn("rr-queue-row", html)
        self.assertIn("rr-policy-panel", html)
        self.assertIn("rr-flow", html)

    def test_risk_queue_has_operating_controls(self) -> None:
        app = self._render("views/risk_queue.py")
        self.assertEqual(len(app.text_input), 1)
        self.assertEqual(len(app.multiselect), 2)
        self.assertEqual(len(app.selectbox), 2)
        self.assertEqual(len(app.download_button), 1)
        self.assertEqual(len(app.dataframe), 1)

    def test_priority_link_opens_detail_and_returns_to_queue(self) -> None:
        app = AppTest.from_file(
            str(APP_DIR / "views/risk_queue.py"),
            default_timeout=45,
        )
        app.query_params["reviewer"] = "demo_reviewer_00001"
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
        self.assertIn("rr-change-story", html)
        self.assertIn("왜 우선 검토 대상인가", html)
        self.assertIn("Recommended playbook", html)
        self.assertIn("rr-future-module", html)
        self.assertEqual(app.toggle[0].label, "검증 정답 표시")
        self.assertEqual(len(app.segmented_control), 1)

    def test_playbook_exposes_future_campaign_structure(self) -> None:
        app = self._render("views/playbook.py")
        html = self._html(app)
        self.assertIn("캠페인 실행과 성과 추적", html)
        self.assertTrue(app.button[0].disabled)

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


if __name__ == "__main__":
    unittest.main()
