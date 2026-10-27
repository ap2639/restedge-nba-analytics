from pathlib import Path

import pandas as pd

from analytics import build_processed_games


base_dir = Path(__file__).resolve().parent
raw_data_path = base_dir / "data" / "player_games_2025_26.csv"
processed_data_path = base_dir / "data" / "processed_player_games.csv"

# Load the preserved API output and calculate both definitions of rest.
games = pd.read_csv(raw_data_path)
combined = build_processed_games(games)

# Save the derived dataset. The raw CSV is never overwritten.
combined.to_csv(processed_data_path, index=False)

print("Original records:", len(games))
print("Processed records:", len(combined))
print("Teams:", combined["TEAM_ID"].nunique())

print("\nSample of processed player data:")

print(
    combined[
        [
            "PLAYER_NAME",
            "GAME_DATE",
            "PTS",
            "TEAM_DAYS_OFF",
            "PLAYER_DAYS_OFF",
        ]
    ].head(10)
)
