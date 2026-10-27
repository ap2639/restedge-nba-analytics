import unittest

import pandas as pd

from analytics import (
    REST_CATEGORY_ORDER,
    build_processed_games,
    categorize_rest,
    summarize_by_rest,
)


class RestCategoryTests(unittest.TestCase):
    def test_rest_categories_match_schedule_meaning(self):
        result = categorize_rest(pd.Series([0, 1, 2, 5, None]))

        self.assertEqual(result.iloc[0], "Back-to-back")
        self.assertEqual(result.iloc[1], "1 day off")
        self.assertEqual(result.iloc[2], "2+ days off")
        self.assertEqual(result.iloc[3], "2+ days off")
        self.assertTrue(pd.isna(result.iloc[4]))


class HistoricalSummaryTests(unittest.TestCase):
    def test_summary_uses_actual_over_results_and_samples(self):
        games = pd.DataFrame(
            {
                "PTS": [20, 26, 24, 30, 25, 10],
                "TEAM_DAYS_OFF": [0, 0, 1, 1, 2, 3],
                "PLAYER_DAYS_OFF": [0, 0, 1, 1, 2, 3],
            }
        )

        summary = summarize_by_rest(games, "PTS", 24.5, "TEAM_DAYS_OFF")

        self.assertEqual(tuple(summary["REST_CATEGORY"]), REST_CATEGORY_ORDER)
        self.assertEqual(summary["GAMES"].tolist(), [2, 2, 2])
        self.assertEqual(summary["HITS"].tolist(), [1, 1, 1])
        self.assertEqual(summary["HIT_RATE"].tolist(), [0.5, 0.5, 0.5])

    def test_empty_category_is_retained_without_inventing_a_rate(self):
        games = pd.DataFrame(
            {
                "PTS": [21, 25],
                "TEAM_DAYS_OFF": [1, 2],
                "PLAYER_DAYS_OFF": [1, 2],
            }
        )

        summary = summarize_by_rest(games, "PTS", 20.5, "TEAM_DAYS_OFF")

        self.assertEqual(summary.iloc[0]["GAMES"], 0)
        self.assertTrue(pd.isna(summary.iloc[0]["HIT_RATE"]))


class RestMergeTests(unittest.TestCase):
    def test_rest_merge_preserves_rows_and_separates_rest_types(self):
        games = pd.DataFrame(
            {
                "PLAYER_ID": [1, 2, 2, 1, 2],
                "PLAYER_NAME": ["A", "B", "B", "A", "B"],
                "TEAM_ID": [10, 10, 10, 10, 10],
                "TEAM_ABBREVIATION": ["TST"] * 5,
                "GAME_ID": [100, 100, 101, 102, 102],
                "GAME_DATE": [
                    "2026-01-01",
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-04",
                    "2026-01-04",
                ],
                "PTS": [10, 11, 12, 13, 14],
            }
        )

        processed = build_processed_games(games)
        player_a_return = processed[
            (processed["PLAYER_ID"] == 1) & (processed["GAME_ID"] == 102)
        ].iloc[0]

        self.assertEqual(len(processed), len(games))
        self.assertEqual(player_a_return["TEAM_DAYS_OFF"], 1)
        self.assertEqual(player_a_return["PLAYER_DAYS_OFF"], 2)


if __name__ == "__main__":
    unittest.main()
