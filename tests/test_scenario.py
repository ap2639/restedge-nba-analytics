import unittest

import pandas as pd

from scenario import build_scenario_projection


class ScenarioTests(unittest.TestCase):
    def test_expected_minutes_and_manual_adjustment_change_projection(self):
        games = pd.DataFrame(
            {
                "GAME_DATE": pd.date_range("2025-10-01", periods=12),
                "MIN": [30] * 12,
                "PTS": [15] * 12,
                "TEAM_DAYS_OFF": [1] * 12,
            }
        )
        base = build_scenario_projection(games, "PTS", 30, "1 day off")
        changed = build_scenario_projection(
            games, "PTS", 36, "1 day off", manual_adjustment=2
        )
        self.assertAlmostEqual(base.projection, 15)
        self.assertAlmostEqual(changed.projection, 20)


if __name__ == "__main__":
    unittest.main()

