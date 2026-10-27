import unittest

import pandas as pd

from modeling import (
    chronological_player_backtest,
    normal_over_probability,
    prior_season_to_current_backtest,
)


def games_frame(count=30):
    return pd.DataFrame(
        {
            "GAME_DATE": pd.date_range("2025-10-01", periods=count, freq="2D"),
            "MATCHUP": ["TST vs. DEM"] * count,
            "PTS": [18 + index % 12 for index in range(count)],
            "TEAM_DAYS_OFF": [0 if index % 5 == 0 else 1 for index in range(count)],
            "PLAYER_DAYS_OFF": [0 if index % 5 == 0 else 1 for index in range(count)],
        }
    )


class ModelingTests(unittest.TestCase):
    def test_probability_moves_with_projection(self):
        self.assertGreater(
            normal_over_probability(28, 5, 24.5),
            normal_over_probability(20, 5, 24.5),
        )

    def test_backtest_uses_only_prior_games(self):
        original, _ = chronological_player_backtest(
            games_frame(30), "PTS", 24.5, "TEAM_DAYS_OFF"
        )
        extended = games_frame(31)
        extended.loc[30, "PTS"] = 100
        updated, _ = chronological_player_backtest(
            extended, "PTS", 24.5, "TEAM_DAYS_OFF"
        )
        pd.testing.assert_series_equal(
            original["BASELINE_MEAN"],
            updated.iloc[: len(original)]["BASELINE_MEAN"],
            check_names=False,
        )

    def test_backtest_reports_both_models(self):
        predictions, metrics = chronological_player_backtest(
            games_frame(), "PTS", 24.5, "TEAM_DAYS_OFF"
        )
        self.assertFalse(predictions.empty)
        self.assertEqual(metrics["Model"].tolist(), ["Rolling baseline", "Rest-aware"])

    def test_prior_season_model_evaluates_current_games(self):
        historical = games_frame(30)
        current = games_frame(5)
        current["GAME_DATE"] = pd.date_range("2026-10-20", periods=5, freq="2D")

        predictions, metrics = prior_season_to_current_backtest(
            historical, current, "PTS", 24.5, "TEAM_DAYS_OFF"
        )

        self.assertEqual(len(predictions), 5)
        self.assertEqual(predictions.iloc[0]["PRIOR_GAMES"], 30)
        self.assertEqual(predictions.iloc[-1]["PRIOR_GAMES"], 34)
        self.assertEqual(
            metrics["Model"].tolist(),
            ["Prior-season baseline", "Prior-season rest-aware"],
        )

    def test_current_result_only_changes_later_current_predictions(self):
        historical = games_frame(30)
        current = games_frame(5)
        current["GAME_DATE"] = pd.date_range("2026-10-20", periods=5, freq="2D")
        original, _ = prior_season_to_current_backtest(
            historical, current, "PTS", 24.5, "TEAM_DAYS_OFF"
        )
        current.loc[4, "PTS"] = 100
        updated, _ = prior_season_to_current_backtest(
            historical, current, "PTS", 24.5, "TEAM_DAYS_OFF"
        )
        pd.testing.assert_series_equal(
            original.iloc[:4]["BASELINE_MEAN"].reset_index(drop=True),
            updated.iloc[:4]["BASELINE_MEAN"].reset_index(drop=True),
            check_names=False,
        )


if __name__ == "__main__":
    unittest.main()

