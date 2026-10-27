import json
import unittest
from pathlib import Path

from analytics import load_processed_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RepositoryDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = load_processed_data(
            PROJECT_ROOT / "data" / "processed_player_games.csv"
        )

    def test_expected_season_data_is_present(self):
        self.assertEqual(len(self.games), 26_651)
        self.assertEqual(self.games["TEAM_ID"].nunique(), 30)
        self.assertEqual(self.games["PLAYER_ID"].nunique(), 582)

    def test_player_game_rows_are_unique(self):
        duplicates = self.games.duplicated(subset=["PLAYER_ID", "GAME_ID"]).sum()
        self.assertEqual(duplicates, 0)

    def test_rest_columns_have_expected_first_record_gaps(self):
        self.assertEqual(self.games["PLAYER_DAYS_OFF"].isna().sum(), 582)
        self.assertEqual(self.games["TEAM_DAYS_OFF"].isna().sum(), 332)

    def test_current_season_dataset_matches_public_metadata(self):
        processed_path = (
            PROJECT_ROOT
            / "data"
            / "season_store"
            / "processed"
            / "player_games_2026_27.csv.gz"
        )
        metadata_path = (
            PROJECT_ROOT
            / "data"
            / "season_store"
            / "metadata"
            / "player_games_2026_27.json"
        )
        current_games = load_processed_data(processed_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(len(current_games), metadata["player_game_records"])
        self.assertEqual(current_games["TEAM_ID"].nunique(), metadata["teams"])
        self.assertEqual(current_games["PLAYER_ID"].nunique(), metadata["players"])
        self.assertEqual(
            current_games["GAME_DATE"].max().date().isoformat(),
            metadata["last_game_date"],
        )
        self.assertEqual(
            current_games.duplicated(subset=["PLAYER_ID", "GAME_ID"]).sum(),
            0,
        )


if __name__ == "__main__":
    unittest.main()
