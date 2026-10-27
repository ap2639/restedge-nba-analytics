"""Versioned NBA season ingestion for current and historical RestEdge data."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from analytics import REQUIRED_PROCESSED_COLUMNS, build_processed_games


RAW_REQUIRED_COLUMNS = REQUIRED_PROCESSED_COLUMNS.difference(
    {"TEAM_DAYS_OFF", "PLAYER_DAYS_OFF"}
)


def season_slug(season: str) -> str:
    """Convert an NBA season label such as 2026-27 to a file-safe slug."""
    parts = season.split("-")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValueError("Season must use NBA format YYYY-YY, for example 2026-27.")
    if not all(part.isdigit() for part in parts):
        raise ValueError("Season must contain only digits and one hyphen.")
    expected_end = (int(parts[0]) + 1) % 100
    if int(parts[1]) != expected_end:
        raise ValueError("Season end year must follow the start year.")
    return season.replace("-", "_")


def validate_raw_games(games: pd.DataFrame) -> pd.DataFrame:
    """Validate an NBA player-game response before saving or processing it."""
    if games.empty:
        raise ValueError("NBA player-game response is empty.")

    missing = RAW_REQUIRED_COLUMNS.difference(games.columns)
    if missing:
        raise ValueError(f"Raw data is missing required columns: {', '.join(sorted(missing))}")

    validated = games.copy()
    validated["GAME_DATE"] = pd.to_datetime(validated["GAME_DATE"], errors="raise")
    duplicate_mask = validated.duplicated(
        subset=["PLAYER_ID", "GAME_ID"], keep=False
    )
    resolved_count = 0
    if duplicate_mask.any():
        resolved_groups = [validated.loc[~duplicate_mask]]
        duplicate_rows = validated.loc[duplicate_mask]
        for _, group in duplicate_rows.groupby(["PLAYER_ID", "GAME_ID"], sort=False):
            if len(group.drop_duplicates()) == 1:
                resolved_groups.append(group.iloc[[0]])
                resolved_count += len(group) - 1
                continue

            minutes = pd.to_numeric(group["MIN"], errors="coerce").fillna(0)
            positive_minutes = minutes > 0
            if positive_minutes.sum() == 1 and (minutes.loc[~positive_minutes] == 0).all():
                resolved_groups.append(group.loc[positive_minutes])
                resolved_count += len(group) - 1
                continue

            player_id = group.iloc[0]["PLAYER_ID"]
            game_id = group.iloc[0]["GAME_ID"]
            raise ValueError(
                "Raw data contains an ambiguous duplicate player-game record "
                f"for player {player_id} in game {game_id}."
            )
        validated = pd.concat(resolved_groups, ignore_index=True)

    validated = validated.sort_values(
        ["GAME_DATE", "GAME_ID", "PLAYER_ID"]
    ).reset_index(drop=True)
    validated.attrs["resolved_duplicate_player_game_rows"] = resolved_count
    return validated


def fetch_player_games(season: str, timeout: int = 60) -> pd.DataFrame:
    """Fetch regular-season player game logs from the installed nba_api client."""
    from nba_api.stats.endpoints import playergamelogs

    response = playergamelogs.PlayerGameLogs(
        season_nullable=season,
        season_type_nullable="Regular Season",
        timeout=timeout,
    )
    return response.get_data_frames()[0]


def build_metadata(
    raw_games: pd.DataFrame,
    processed_games: pd.DataFrame,
    season: str,
    fetched_at: datetime,
) -> dict:
    """Create the public freshness record displayed by future app releases."""
    game_dates = pd.to_datetime(processed_games["GAME_DATE"])
    return {
        "season": season,
        "source": "NBA stats player game logs",
        "fetched_at_utc": fetched_at.astimezone(timezone.utc).isoformat(),
        "first_game_date": game_dates.min().date().isoformat(),
        "last_game_date": game_dates.max().date().isoformat(),
        "player_game_records": int(len(processed_games)),
        "players": int(processed_games["PLAYER_ID"].nunique()),
        "teams": int(processed_games["TEAM_ID"].nunique()),
        "raw_columns": int(len(raw_games.columns)),
        "processed_columns": int(len(processed_games.columns)),
        "resolved_duplicate_player_game_rows": int(
            raw_games.attrs.get("resolved_duplicate_player_game_rows", 0)
        ),
    }


def write_season_dataset(
    games: pd.DataFrame,
    season: str,
    data_root: str | Path,
    fetched_at: datetime | None = None,
) -> dict[str, Path | dict]:
    """Validate, version, process, and describe one season dataset."""
    slug = season_slug(season)
    fetched_at = fetched_at or datetime.now(timezone.utc)
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    data_root = Path(data_root)
    snapshot_dir = data_root / "raw" / slug
    processed_dir = data_root / "processed"
    metadata_dir = data_root / "metadata"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    raw_games = validate_raw_games(games)
    processed_games = build_processed_games(raw_games)
    metadata = build_metadata(raw_games, processed_games, season, fetched_at)

    stamp = fetched_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = snapshot_dir / f"player_games_{stamp}.csv.gz"
    latest_raw_path = data_root / "raw" / f"player_games_{slug}_latest.csv.gz"
    processed_path = processed_dir / f"player_games_{slug}.csv.gz"
    metadata_path = metadata_dir / f"player_games_{slug}.json"

    raw_games.to_csv(snapshot_path, index=False, compression="gzip")
    raw_games.to_csv(latest_raw_path, index=False, compression="gzip")
    processed_games.to_csv(processed_path, index=False, compression="gzip")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return {
        "snapshot_path": snapshot_path,
        "latest_raw_path": latest_raw_path,
        "processed_path": processed_path,
        "metadata_path": metadata_path,
        "metadata": metadata,
    }


def refresh_season(
    season: str,
    data_root: str | Path,
    timeout: int = 60,
    fetcher: Callable[[str, int], pd.DataFrame] = fetch_player_games,
) -> dict[str, Path | dict]:
    """Fetch and persist one complete season refresh."""
    games = fetcher(season, timeout)
    return write_season_dataset(games, season, data_root)

