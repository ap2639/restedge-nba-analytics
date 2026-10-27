from pathlib import Path

from analytics import load_processed_data, summarize_by_rest


base_dir = Path(__file__).resolve().parent
games = load_processed_data(base_dir / "data" / "processed_player_games.csv")

# Select the player we want to analyze
player_name = "LeBron James"

player_games = games[
    games["PLAYER_NAME"] == player_name
].copy()

summary = summarize_by_rest(
    player_games,
    stat_column="PTS",
    line=24.5,
    rest_column="TEAM_DAYS_OFF",
)

# Make the results easier to read
summary["AVERAGE"] = summary["AVERAGE"].round(2)
summary["HIT_RATE"] = (summary["HIT_RATE"] * 100).round(1)
summary = summary.rename(columns={"AVERAGE": "AVG_POINTS"})

print("\nPerformance analysis:", player_name)
print(summary.to_string(index=False))
