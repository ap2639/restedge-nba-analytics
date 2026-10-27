from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import playergamelogs

base_dir = Path(__file__).resolve().parent
data_folder = base_dir / "data"
data_folder.mkdir(exist_ok=True)

file_path = data_folder / "player_games_2025_26.csv"

if file_path.exists():
    games = pd.read_csv(file_path)
    print("Loaded saved NBA data.")

else:
    response = playergamelogs.PlayerGameLogs(
        season_nullable="2025-26",
        season_type_nullable="Regular Season",
        timeout=30
    )

    games = response.get_data_frames()[0]
    games.to_csv(file_path, index=False)
    print("Downloaded NBA data.")

print("Total player-game records:", len(games))

print(games[
    ["PLAYER_NAME", "GAME_DATE", "MIN", "PTS", "FG_PCT"]
].head())
