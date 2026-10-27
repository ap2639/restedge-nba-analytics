import unittest
from unittest.mock import patch
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def test_dashboard_renders_and_controls_recalculate(self):
        app = AppTest.from_file(
            str(PROJECT_ROOT / "app.py"), default_timeout=20
        ).run()

        self.assertFalse(app.exception)
        self.assertEqual(len(app.selectbox), 3)
        self.assertEqual(len(app.number_input), 1)
        self.assertEqual(len(app.dataframe), 0)
        self.assertEqual(len(app.get("plotly_chart")), 1)
        self.assertGreaterEqual(len(app.get("html")), 12)
        self.assertEqual(len(app.code), 0)

        rendered_html = "\n".join(block.value for block in app.get("html"))
        for page in [
            "home", "slate", "markets", "players", "scenario-lab", "news",
            "model-lab", "methodology",
        ]:
            self.assertIn(f'href="?page={page}"', rendered_html)

        app.selectbox[1].set_value("Rebounds").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input[0].value, 7.5)

        app.selectbox[2].set_value("Player appearances").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox[2].value, "Player appearances")

    def test_each_navigation_destination_renders(self):
        expected_components = {
            "home": (3, 1, 1),
            "slate": (0, 0, 0),
            "markets": (3, 1, 1),
            "players": (3, 1, 1),
            "scenario-lab": (4, 3, 0),
            "news": (1, 0, 0),
            "model-lab": (3, 1, None),
            "methodology": (0, 0, 0),
        }

        for page, (selectboxes, number_inputs, charts) in expected_components.items():
            with self.subTest(page=page):
                with patch.dict("os.environ", {"RESTEDGE_LIVE_NEWS": "0"}):
                    app = AppTest.from_file(
                        str(PROJECT_ROOT / "app.py"), default_timeout=20
                    )
                    app.query_params["page"] = page
                    app.run()

                self.assertFalse(app.exception)
                self.assertEqual(len(app.selectbox), selectboxes)
                self.assertEqual(len(app.number_input), number_inputs)
                if charts is None:
                    self.assertIn(len(app.get("plotly_chart")), {0, 1})
                else:
                    self.assertEqual(len(app.get("plotly_chart")), charts)
                self.assertEqual(len(app.dataframe), 0)
                self.assertEqual(len(app.code), 0)


if __name__ == "__main__":
    unittest.main()
