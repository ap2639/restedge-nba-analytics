"""Transparent assumption-based player prop scenario calculations."""

from dataclasses import asdict, dataclass

import pandas as pd

from analytics import categorize_rest


@dataclass(frozen=True)
class ScenarioProjection:
    projection: float
    recent_per_minute_rate: float
    expected_minutes: float
    rest_adjustment: float
    manual_adjustment: float
    rest_sample: int

    def to_dict(self) -> dict:
        return asdict(self)


def build_scenario_projection(
    player_games: pd.DataFrame,
    stat_column: str,
    expected_minutes: float,
    rest_category: str,
    manual_adjustment: float = 0.0,
    recent_games: int = 10,
) -> ScenarioProjection:
    """Project a selected statistic from minutes, recent rate, and a rest split."""
    eligible = player_games.dropna(subset=[stat_column, "MIN", "TEAM_DAYS_OFF"]).copy()
    eligible = eligible[eligible["MIN"] > 0].sort_values("GAME_DATE")
    if eligible.empty:
        raise ValueError("No eligible player games are available for this scenario.")

    eligible["REST_CATEGORY"] = categorize_rest(eligible["TEAM_DAYS_OFF"]).astype(str)
    eligible["PER_MINUTE"] = eligible[stat_column] / eligible["MIN"]
    recent = eligible.tail(recent_games)
    recent_rate = float(recent["PER_MINUTE"].median())

    rest_games = eligible[eligible["REST_CATEGORY"] == rest_category]
    rest_adjustment = 0.0
    if len(rest_games) >= 5:
        overall_rate = float(eligible["PER_MINUTE"].median())
        rest_rate = float(rest_games["PER_MINUTE"].median())
        rest_adjustment = (rest_rate - overall_rate) * expected_minutes

    projection = recent_rate * expected_minutes + rest_adjustment + manual_adjustment
    return ScenarioProjection(
        projection=max(projection, 0.0),
        recent_per_minute_rate=recent_rate,
        expected_minutes=float(expected_minutes),
        rest_adjustment=rest_adjustment,
        manual_adjustment=float(manual_adjustment),
        rest_sample=len(rest_games),
    )

