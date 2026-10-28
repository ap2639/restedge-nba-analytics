import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from requests.exceptions import ReadTimeout

from scripts import update_season


class SeasonUpdaterTests(unittest.TestCase):
    def test_refresh_retries_transient_source_failures(self):
        calls = []
        delays = []
        expected = {"metadata": {"season": "2026-27"}}

        def refresh(season, data_root, timeout):
            calls.append((season, data_root, timeout))
            if len(calls) < 3:
                raise ReadTimeout("source timed out")
            return expected

        result = update_season.refresh_with_retries(
            "2026-27",
            Path("data"),
            timeout=45,
            attempts=3,
            retry_delay_seconds=2,
            refresh=refresh,
            sleep=delays.append,
        )

        self.assertIs(result, expected)
        self.assertEqual(len(calls), 3)
        self.assertEqual(delays, [2, 2])

    def test_existing_status_requires_readable_data_and_matching_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            processed_dir = data_root / "processed"
            metadata_dir = data_root / "metadata"
            processed_dir.mkdir()
            metadata_dir.mkdir()
            pd.DataFrame([{"PLAYER_ID": 1}]).to_csv(
                processed_dir / "player_games_2026_27.csv.gz",
                index=False,
                compression="gzip",
            )
            (metadata_dir / "player_games_2026_27.json").write_text(
                json.dumps({"season": "2026-27", "last_game_date": "2026-10-26"}),
                encoding="utf-8",
            )

            status = update_season.read_existing_status("2026-27", data_root)

        self.assertEqual(status["last_game_date"], "2026-10-26")

    def test_main_keeps_validated_data_when_source_remains_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            processed_dir = data_root / "processed"
            metadata_dir = data_root / "metadata"
            processed_dir.mkdir()
            metadata_dir.mkdir()
            pd.DataFrame([{"PLAYER_ID": 1}]).to_csv(
                processed_dir / "player_games_2026_27.csv.gz",
                index=False,
                compression="gzip",
            )
            (metadata_dir / "player_games_2026_27.json").write_text(
                json.dumps({"season": "2026-27", "last_game_date": "2026-10-26"}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                season="2026-27",
                data_root=data_root,
                timeout=45,
                attempts=3,
                retry_delay_seconds=0,
                keep_existing_on_source_unavailable=True,
                from_csv=None,
            )

            with patch.object(update_season, "parse_args", return_value=args), patch.object(
                update_season,
                "refresh_with_retries",
                side_effect=ReadTimeout("source timed out"),
            ):
                exit_code = update_season.main()

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
