"""Leakage-aware baseline and rest-aware historical backtesting."""

import math

import pandas as pd

from analytics import categorize_rest


def normal_over_probability(mean: float, standard_deviation: float, line: float) -> float:
    """Approximate an over probability with a normal outcome distribution."""
    if pd.isna(mean) or pd.isna(standard_deviation):
        return float("nan")
    standard_deviation = max(float(standard_deviation), 1.0)
    z_score = (line - mean) / standard_deviation
    cdf = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
    return min(max(1 - cdf, 0.001), 0.999)


def _metrics(predictions: pd.DataFrame, probability_column: str, mean_column: str) -> dict:
    probabilities = predictions[probability_column].clip(0.001, 0.999)
    outcomes = predictions["OUTCOME"].astype(float)
    log_loss = -(
        outcomes * probabilities.map(math.log)
        + (1 - outcomes) * (1 - probabilities).map(math.log)
    ).mean()
    return {
        "Brier score": float(((probabilities - outcomes) ** 2).mean()),
        "Log loss": float(log_loss),
        "Mean absolute error": float(
            (predictions[mean_column] - predictions["ACTUAL"]).abs().mean()
        ),
        "Average predicted over": float(probabilities.mean()),
        "Observed over rate": float(outcomes.mean()),
    }


def chronological_player_backtest(
    player_games: pd.DataFrame,
    stat_column: str,
    line: float,
    rest_column: str,
    window: int = 10,
    minimum_history: int = 10,
    minimum_rest_history: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Backtest rolling forecasts using only games played before each prediction."""
    if rest_column not in {"TEAM_DAYS_OFF", "PLAYER_DAYS_OFF"}:
        raise ValueError(f"Unknown rest column: {rest_column}")
    if stat_column not in player_games.columns:
        raise ValueError(f"Unknown statistic column: {stat_column}")

    eligible = player_games.dropna(subset=[stat_column, rest_column, "GAME_DATE"]).copy()
    eligible["GAME_DATE"] = pd.to_datetime(eligible["GAME_DATE"])
    eligible = eligible.sort_values("GAME_DATE").reset_index(drop=True)
    eligible["REST_CATEGORY"] = categorize_rest(eligible[rest_column]).astype(str)

    rows = []
    for index in range(minimum_history, len(eligible)):
        current = eligible.iloc[index]
        history = eligible.iloc[:index]
        recent = history.tail(window)
        baseline_mean = float(recent[stat_column].mean())
        deviation = recent[stat_column].std(ddof=1)
        if pd.isna(deviation):
            deviation = history[stat_column].std(ddof=1)
        deviation = max(float(deviation) if not pd.isna(deviation) else 1.0, 1.0)

        same_rest = history[history["REST_CATEGORY"] == current["REST_CATEGORY"]].tail(window)
        rest_adjustment = 0.0
        if len(same_rest) >= minimum_rest_history:
            rest_adjustment = float(same_rest[stat_column].mean() - recent[stat_column].mean())
            rest_adjustment = max(min(rest_adjustment, deviation * 0.35), -deviation * 0.35)

        rest_mean = baseline_mean + rest_adjustment
        rows.append(
            {
                "GAME_DATE": current["GAME_DATE"],
                "MATCHUP": current.get("MATCHUP", ""),
                "REST_CATEGORY": current["REST_CATEGORY"],
                "ACTUAL": float(current[stat_column]),
                "OUTCOME": bool(current[stat_column] > line),
                "BASELINE_MEAN": baseline_mean,
                "REST_MEAN": rest_mean,
                "REST_ADJUSTMENT": rest_adjustment,
                "BASELINE_PROBABILITY": normal_over_probability(
                    baseline_mean, deviation, line
                ),
                "REST_PROBABILITY": normal_over_probability(rest_mean, deviation, line),
            }
        )

    predictions = pd.DataFrame(rows)
    if predictions.empty:
        return predictions, pd.DataFrame()

    metrics = []
    for model, probability, mean in [
        ("Rolling baseline", "BASELINE_PROBABILITY", "BASELINE_MEAN"),
        ("Rest-aware", "REST_PROBABILITY", "REST_MEAN"),
    ]:
        row = {"Model": model, "Games": len(predictions)}
        row.update(_metrics(predictions, probability, mean))
        metrics.append(row)
    return predictions, pd.DataFrame(metrics)

