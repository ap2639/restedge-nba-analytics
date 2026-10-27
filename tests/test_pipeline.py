import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pipeline import season_slug, validate_raw_games, write_season_dataset


def sample_games() -> pd.DataFrame:
    rows = []
    for game_id, game_date, points in [
        ("100", "2026-10-20", (20, 12)),
        ("101", "2026-10-22", (24, 15)),
    ]:
        for player_id, player_name, player_points in [
            (1, "Player One", points[0]),
            (2, "Player Two", points[1]),
        ]:
            rows.append(
                {
                    "PLAYER_ID": player_id,
                    "PLAYER_NAME": player_name,
                    "TEAM_ID": 10,
                    "TEAM_ABBREVIATION": "TST",
                    "GAME_ID": game_id,
                    "GAME_DATE": game_date,
                    "MATCHUP": "TST vs. DEM",
                    "MIN": 30,
                    "PTS": player_points,
                    "REB": 5,
                    "AST": 4,
                }
            )
    return pd.DataFrame(rows)


class SeasonPipelineTests(unittest.TestCase):
    def test_season_slug_validates_nba_format(self):
        self.assertEqual(season_slug("2026-27"), "2026_27")
        with self.assertRaises(ValueError):
            season_slug("2026-28")

    def test_validation_removes_exact_duplicate_player_games(self):
        games = sample_games()
        games = pd.concat([games, games.iloc[[0]]], ignore_index=True)
        validated = validate_raw_games(games)
        self.assertEqual(len(validated), 4)
        self.assertEqual(validated.attrs["resolved_duplicate_player_game_rows"], 1)

    def test_validation_prefers_the_only_positive_minutes_duplicate(self):
        games = sample_games()
        bad_row = games.iloc[[0]].copy()
        bad_row["TEAM_ID"] = 99
        bad_row["TEAM_ABBREVIATION"] = "BAD"
        bad_row["MIN"] = 0
        games = pd.concat([games, bad_row], ignore_index=True)
        validated = validate_raw_games(games)
        player_game = validated[
            (validated["PLAYER_ID"] == 1) & (validated["GAME_ID"] == "100")
        ]
        self.assertEqual(len(player_game), 1)
        self.assertEqual(player_game.iloc[0]["TEAM_ABBREVIATION"], "TST")

    def test_validation_rejects_ambiguous_duplicate_player_games(self):
        games = sample_games()
        conflicting_row = games.iloc[[0]].copy()
        conflicting_row["PTS"] = 99
        games = pd.concat([games, conflicting_row], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "ambiguous duplicate"):
            validate_raw_games(games)

    def test_writer_preserves_snapshot_and_builds_metadata(self):
        fetched_at = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            result = write_season_dataset(
                sample_games(), "2026-27", directory, fetched_at
            )

            for key in ["snapshot_path", "latest_raw_path", "processed_path", "metadata_path"]:
                self.assertTrue(Path(result[key]).exists())

            processed = pd.read_csv(result["processed_path"])
            self.assertIn("TEAM_DAYS_OFF", processed.columns)
            self.assertIn("PLAYER_DAYS_OFF", processed.columns)
            self.assertEqual(len(processed), 4)

            metadata = json.loads(Path(result["metadata_path"]).read_text())
            self.assertEqual(metadata["season"], "2026-27")
            self.assertEqual(metadata["last_game_date"], "2026-10-22")
            self.assertEqual(metadata["player_game_records"], 4)


if __name__ == "__main__":
    unittest.main()

