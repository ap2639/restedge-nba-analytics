"""Reusable calculations for the RestEdge dashboard and data pipeline."""

from pathlib import Path

import pandas as pd


REST_CATEGORY_ORDER = ("Back-to-back", "1 day off", "2+ days off")

MARKETS = {
    "Points": {
        "column": "PTS",
        "default_line": 24.5,
        "min_line": 0.5,
        "max_line": 59.5,
    },
    "Rebounds": {
        "column": "REB",
        "default_line": 7.5,
        "min_line": 0.5,
        "max_line": 24.5,
    },
    "Assists": {
        "column": "AST",
        "default_line": 5.5,
        "min_line": 0.5,
        "max_line": 19.5,
    },
}

REQUIRED_PROCESSED_COLUMNS = {
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM_ID",
    "TEAM_ABBREVIATION",
    "GAME_ID",
    "GAME_DATE",
    "MATCHUP",
    "MIN",
    "PTS",
    "REB",
    "AST",
    "TEAM_DAYS_OFF",
    "PLAYER_DAYS_OFF",
}


def load_processed_data(file_path: str | Path) -> pd.DataFrame:
    """Load processed player-game data and validate dashboard requirements."""
    games = pd.read_csv(file_path)
    missing_columns = REQUIRED_PROCESSED_COLUMNS.difference(games.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Processed data is missing required columns: {missing}")

    games["GAME_DATE"] = pd.to_datetime(games["GAME_DATE"], errors="raise")
    return games


def calculate_team_rest(games: pd.DataFrame) -> pd.DataFrame:
    """Return one row per team-game with full days off before that game."""
    team_games = games[
        ["TEAM_ID", "TEAM_ABBREVIATION", "GAME_ID", "GAME_DATE"]
    ].copy()
    team_games["GAME_DATE"] = pd.to_datetime(team_games["GAME_DATE"])
    team_games = team_games.drop_duplicates(subset=["TEAM_ID", "GAME_ID"])
    team_games = team_games.sort_values(["TEAM_ID", "GAME_DATE"])
    team_games["TEAM_DAYS_OFF"] = (
        team_games.groupby("TEAM_ID")["GAME_DATE"].diff().dt.days - 1
    )
    return team_games


def calculate_player_rest(games: pd.DataFrame) -> pd.DataFrame:
    """Return player-game rows with full days off since each prior appearance."""
    player_games = games.copy()
    player_games["GAME_DATE"] = pd.to_datetime(player_games["GAME_DATE"])
    player_games = player_games.sort_values(["PLAYER_ID", "GAME_DATE"])
    player_games["PLAYER_DAYS_OFF"] = (
        player_games.groupby("PLAYER_ID")["GAME_DATE"].diff().dt.days - 1
    )
    return player_games


def build_processed_games(games: pd.DataFrame) -> pd.DataFrame:
    """Attach team and player rest while preserving one row per player-game."""
    source = games.drop(
        columns=["TEAM_DAYS_OFF", "PLAYER_DAYS_OFF"], errors="ignore"
    )
    team_games = calculate_team_rest(source)
    player_games = calculate_player_rest(source)

    combined = player_games.merge(
        team_games[["TEAM_ID", "GAME_ID", "TEAM_DAYS_OFF"]],
        on=["TEAM_ID", "GAME_ID"],
        how="left",
        validate="many_to_one",
    )

    if len(combined) != len(source):
        raise ValueError("Rest merge changed the number of player-game records.")

    return combined


def categorize_rest(days_off: pd.Series) -> pd.Series:
    """Map numeric days off to the three dashboard rest categories."""
    return pd.cut(
        days_off,
        bins=[-1, 0, 1, float("inf")],
        labels=REST_CATEGORY_ORDER,
    )


def summarize_by_rest(
    player_games: pd.DataFrame,
    stat_column: str,
    line: float,
    rest_column: str,
) -> pd.DataFrame:
    """Calculate actual performance and over rates for each rest category."""
    if stat_column not in player_games.columns:
        raise ValueError(f"Unknown statistic column: {stat_column}")
    if rest_column not in {"TEAM_DAYS_OFF", "PLAYER_DAYS_OFF"}:
        raise ValueError(f"Unknown rest column: {rest_column}")

    eligible = player_games.dropna(subset=[stat_column, rest_column]).copy()
    eligible["REST_CATEGORY"] = categorize_rest(eligible[rest_column])
    eligible["HIT"] = eligible[stat_column] > line

    rows = []
    for category in REST_CATEGORY_ORDER:
        category_games = eligible[eligible["REST_CATEGORY"] == category]
        game_count = len(category_games)
        hit_count = int(category_games["HIT"].sum())
        hit_rate = hit_count / game_count if game_count else float("nan")

        rows.append(
            {
                "REST_CATEGORY": category,
                "GAMES": game_count,
                "AVERAGE": category_games[stat_column].mean(),
                "HITS": hit_count,
                "HIT_RATE": hit_rate,
            }
        )

    return pd.DataFrame(rows)


def overall_performance(
    player_games: pd.DataFrame,
    stat_column: str,
    line: float,
    rest_column: str,
) -> dict[str, float | int | None]:
    """Calculate the dashboard's overall historical summary."""
    eligible = player_games.dropna(subset=[stat_column, rest_column])
    game_count = len(eligible)
    hit_count = int((eligible[stat_column] > line).sum())
    hit_rate = hit_count / game_count if game_count else float("nan")

    return {
        "games": game_count,
        "average": eligible[stat_column].mean(),
        "hits": hit_count,
        "hit_rate": hit_rate,
    }


def build_player_catalog(games: pd.DataFrame) -> pd.DataFrame:
    """Create searchable labels using each player's latest recorded team."""
    latest = (
        games.sort_values("GAME_DATE")
        .groupby("PLAYER_ID", as_index=False)
        .tail(1)[["PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION"]]
        .copy()
    )
    latest["LABEL"] = (
        latest["PLAYER_NAME"] + " | " + latest["TEAM_ABBREVIATION"]
    )
    return latest.sort_values(["PLAYER_NAME", "PLAYER_ID"]).reset_index(drop=True)
