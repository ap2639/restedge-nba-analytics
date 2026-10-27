"""Command-line entry point for a versioned RestEdge season refresh."""

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import refresh_season, write_season_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh RestEdge NBA season data.")
    parser.add_argument("--season", required=True, help="NBA season in YYYY-YY format.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "season_store",
        help="Versioned data output directory.",
    )
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--from-csv",
        type=Path,
        help="Process an existing raw CSV instead of requesting NBA data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.from_csv:
        result = write_season_dataset(
            pd.read_csv(args.from_csv), args.season, args.data_root
        )
    else:
        result = refresh_season(args.season, args.data_root, args.timeout)

    metadata = result["metadata"]
    print(f"Updated RestEdge {metadata['season']} through {metadata['last_game_date']}.")
    print(f"Player-game records: {metadata['player_game_records']}")
    print(f"Processed data: {result['processed_path']}")
    print(f"Metadata: {result['metadata_path']}")


if __name__ == "__main__":
    main()

