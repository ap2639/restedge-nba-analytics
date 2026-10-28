"""Command-line entry point for a versioned RestEdge season refresh."""

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from requests.exceptions import RequestException


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import refresh_season, write_season_dataset


TRANSIENT_REFRESH_EXCEPTIONS = (RequestException, TimeoutError, json.JSONDecodeError)


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
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=float, default=15)
    parser.add_argument(
        "--keep-existing-on-source-unavailable",
        action="store_true",
        help="Keep the last validated dataset when the NBA source remains unavailable.",
    )
    parser.add_argument(
        "--from-csv",
        type=Path,
        help="Process an existing raw CSV instead of requesting NBA data.",
    )
    return parser.parse_args()


def refresh_with_retries(
    season: str,
    data_root: Path,
    timeout: int,
    attempts: int,
    retry_delay_seconds: float,
    refresh=refresh_season,
    sleep=time.sleep,
):
    """Retry transient source failures before returning a validated refresh."""
    if attempts < 1:
        raise ValueError("Attempts must be at least 1.")
    if retry_delay_seconds < 0:
        raise ValueError("Retry delay must be non-negative.")

    for attempt in range(1, attempts + 1):
        try:
            return refresh(season, data_root, timeout)
        except TRANSIENT_REFRESH_EXCEPTIONS:
            if attempt == attempts:
                raise
            print(
                f"NBA data source unavailable on attempt {attempt} of {attempts}; "
                f"retrying in {retry_delay_seconds:g} seconds."
            )
            sleep(retry_delay_seconds)

    raise RuntimeError("Refresh attempts finished without a result.")


def read_existing_status(season: str, data_root: Path) -> dict | None:
    """Return metadata only when the existing processed dataset is readable."""
    slug = season.replace("-", "_")
    processed_path = data_root / "processed" / f"player_games_{slug}.csv.gz"
    metadata_path = data_root / "metadata" / f"player_games_{slug}.json"
    if not processed_path.exists() or not metadata_path.exists():
        return None

    try:
        pd.read_csv(processed_path, nrows=1)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None

    if metadata.get("season") != season or not metadata.get("last_game_date"):
        return None
    return metadata


def main() -> int:
    args = parse_args()
    if args.from_csv:
        result = write_season_dataset(
            pd.read_csv(args.from_csv), args.season, args.data_root
        )
    else:
        try:
            result = refresh_with_retries(
                args.season,
                args.data_root,
                args.timeout,
                args.attempts,
                args.retry_delay_seconds,
            )
        except TRANSIENT_REFRESH_EXCEPTIONS as source_exception:
            existing = read_existing_status(args.season, args.data_root)
            if not args.keep_existing_on_source_unavailable or existing is None:
                raise
            print(
                "NBA data source remained unavailable after "
                f"{args.attempts} attempts ({type(source_exception).__name__})."
            )
            print(
                f"Kept the last validated {args.season} dataset through "
                f"{existing['last_game_date']}."
            )
            return 0

    metadata = result["metadata"]
    print(f"Updated RestEdge {metadata['season']} through {metadata['last_game_date']}.")
    print(f"Player-game records: {metadata['player_game_records']}")
    print(f"Processed data: {result['processed_path']}")
    print(f"Metadata: {result['metadata_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

