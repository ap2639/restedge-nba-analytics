import unittest

import pandas as pd

from insights import build_all_rest_insights, build_rest_insight


class RestInsightTests(unittest.TestCase):
    def setUp(self):
        self.summary = pd.DataFrame(
            [
                {"REST_CATEGORY": "Back-to-back", "GAMES": 7, "HITS": 5, "HIT_RATE": 5 / 7},
                {"REST_CATEGORY": "1 day off", "GAMES": 30, "HITS": 20, "HIT_RATE": 2 / 3},
                {"REST_CATEGORY": "2+ days off", "GAMES": 20, "HITS": 6, "HIT_RATE": 0.30},
            ]
        )
        self.overall = {"hit_rate": 0.50}

    def test_small_samples_never_create_a_lean(self):
        insight = build_rest_insight(
            self.summary, self.overall, "Back-to-back", "Points", 24.5
        )
        self.assertEqual(insight.signal, "INSUFFICIENT SAMPLE")
        self.assertEqual(insight.tone, "caution")

    def test_larger_splits_can_describe_higher_and_lower_rates(self):
        higher = build_rest_insight(
            self.summary, self.overall, "1 day off", "Points", 24.5
        )
        lower = build_rest_insight(
            self.summary, self.overall, "2+ days off", "Points", 24.5
        )
        self.assertEqual(higher.signal, "HIGHER HISTORICAL RATE")
        self.assertEqual(lower.signal, "LOWER HISTORICAL RATE")

    def test_all_categories_remain_in_fixed_order(self):
        insights = build_all_rest_insights(
            self.summary, self.overall, "Points", 24.5
        )
        self.assertEqual(
            [insight.category for insight in insights],
            ["Back-to-back", "1 day off", "2+ days off"],
        )


if __name__ == "__main__":
    unittest.main()

