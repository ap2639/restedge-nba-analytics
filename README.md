# RestEdge

[![Tests](https://github.com/ap2639/restedge-nba-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/ap2639/restedge-nba-analytics/actions/workflows/tests.yml)
[![Open RestEdge](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://lgh4tgas5zmq3v5ndxwvid.streamlit.app/)

**Live application:** [Open RestEdge on Streamlit Community Cloud](https://lgh4tgas5zmq3v5ndxwvid.streamlit.app/)

RestEdge is an NBA player-performance research application built with Python,
pandas, Streamlit, and Plotly. It studies how schedule rest relates to points,
rebounds, and assists while keeping descriptive statistics, scenario assumptions,
and model validation clearly separated.

The project is designed as a portfolio demonstration of sports research, data
quality, probability evaluation, automated data pipelines, and analytical
communication. It does not place wagers or provide financial recommendations.

## Current release

| Capability | Current status |
|---|---|
| 2026-27 completed player-game tracking | Active through October 26, 2026 |
| Update frequency | Daily GitHub Actions workflow after deployment |
| Player news | Rest, injury, availability, and workload search, cached for one hour |
| Historical season | Complete 2025-26 regular-season dataset, selectable in the dashboard |
| In-game tracking | Not implemented; the project never labels daily data as real-time |
| Forecasting | 2025-26 history evaluated on completed 2026-27 games without future-data leakage |

The active 2026-27 dataset currently contains **1,181 player-game records**, **411
players**, and **all 30 NBA teams**. The application automatically uses the newest
validated season file. A season switch in the header lets users study either
2025-26 or 2026-27 without combining their descriptive statistics.

## Dashboard tour

- **Home:** player selection, statistic thresholds, team-versus-player rest,
  season profile, rest splits, recent form, and plain-language interpretations.
- **Slate:** the latest completed game date in the active dataset, matchup cards,
  scoring leaders, back-to-back counts, and refresh status.
- **Splits:** threshold sensitivity and side-by-side performance comparisons for
  back-to-backs, one day off, and two or more days off.
- **Players:** player profile, season averages, threshold momentum, and recent
  game results.
- **Scenario Lab:** an assumption calculator for expected minutes, rest scenario,
  and an explicit manual production adjustment.
- **News:** prioritized player-specific injury, availability, rest, workload, and
  minutes-status headlines with publisher, timestamp, and freshness.
- **Model Lab:** 2025-26 player history seeds the 2026-27 evaluation, which then
  updates only from earlier completed current-season games. The historical season
  remains available for a same-season chronological backtest.
- **Methodology:** calculation definitions, limitations, coverage, freshness, and
  dataset-integrity checks.

## What makes the analysis defensible

- Team schedule rest and player appearance rest are calculated separately.
- All threshold rates display their underlying sample sizes.
- Small samples are labeled rather than presented as stable evidence.
- Model evaluation uses chronological history to avoid future-game leakage.
- Live headlines never change a projection automatically.
- Current-season records remain separate from historical descriptive summaries.
- Current-season model evaluation starts with prior-season records and adds each
  2026-27 result only after its prediction has been generated.
- Ambiguous duplicate player-game records stop the update instead of being
  silently accepted. Exact duplicates and a single zero-minute upstream duplicate
  can be resolved through tested rules and are reported in metadata.

## Project structure

```text
app.py                         Streamlit interface and navigation
analytics.py                   reusable rest and threshold calculations
insights.py                    plain-language rest interpretations
modeling.py                    chronological model backtesting
news.py                        live and local player-news adapters
pipeline.py                    validated, versioned season ingestion
scenario.py                    minutes and rest scenario calculations
scripts/update_season.py       current-season refresh command
data/processed_player_games.csv historical processed fallback
data/season_store/processed/   current-season deployment data
data/season_store/metadata/    freshness and coverage metadata
tests/                         unit, application, and repository checks
.github/workflows/             automated tests and daily season refresh
```

## Run locally

```bash
git clone https://github.com/ap2639/restedge-nba-analytics.git
cd restedge-nba-analytics
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

The terminal prints the local dashboard address. Keep that process running while
using the application.

## Run the checks

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The suite covers rest boundaries, team-versus-player rest, threshold rates,
scenario calculations, news validation, chronological modeling, duplicate-data
handling, dataset integrity, and every dashboard destination.

## Refresh the current season

```bash
.venv/bin/python scripts/update_season.py \
  --season 2026-27 \
  --data-root data/season_store
```

The command validates the NBA response, preserves an ignored timestamped raw
snapshot, calculates rest variables, writes a compressed processed dataset, and
creates public freshness metadata. The scheduled GitHub workflow runs the same
pipeline daily and commits only processed data and metadata.

## Player news

The News workspace searches Google News RSS using the selected player's exact
name plus injury, availability, rest, workload, recovery, and minutes-status
terms. Results are limited to seven days, attributed to the publisher, and cached
for one hour. Official and injury updates are ranked before availability and
workload reporting. Unrelated game recaps are filtered out, and a manual refresh
button is available.

Headline classifications are informational. Users should still verify material
availability information through the linked team or NBA source.

## Two-season model design

The newly started 2026-27 season is too small to support a stable standalone
player model. RestEdge therefore uses 2025-26 as the starting history for players
who appeared in both seasons. For every completed 2026-27 game, the model uses the
prior season plus only earlier 2026-27 results. Rookies and players without enough
prior history remain explicitly unavailable rather than receiving invented
estimates.

## Deploy with Streamlit Community Cloud

GitHub Pages cannot execute a Python Streamlit server. The GitHub repository
stores and documents the project; Streamlit Community Cloud hosts the interactive
application. The current public deployment is available at
[lgh4tgas5zmq3v5ndxwvid.streamlit.app](https://lgh4tgas5zmq3v5ndxwvid.streamlit.app/).

1. Push this repository to GitHub.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Select **Create app**.
4. Choose `ap2639/restedge-nba-analytics` and the `main` branch.
5. Set the entry point to `app.py`.
6. Deploy without adding secrets; this release does not require an API key.

The application uses `requirements.txt`, `runtime.txt`, and
`.streamlit/config.toml` during deployment.

## Limitations

- Current-season data refreshes completed games daily; it is not a possession-by-
  possession or in-game feed.
- The research model does not yet include opponent quality, venue, pace, travel,
  expected role, official injury status, or teammate availability.
- News coverage depends on publisher indexing and can be incomplete or delayed.
- Cross-season player roles can change, so prior-season history is a baseline,
  not proof that the current role or production distribution is unchanged.
- Rest relationships are observational and do not establish causation.
- A higher historical threshold rate does not guarantee future performance.

## Planned full version

The next releases will add structured official injury reports, opponent and pace
features, teammate-availability context, travel and workload indicators,
prediction intervals, model-drift monitoring, and a clear change log for every
daily data refresh. See [`ROADMAP.md`](ROADMAP.md) for the detailed sequence.

