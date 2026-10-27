# RestEdge Product Roadmap

RestEdge is progressing from a historical rest-analysis project into a public,
current-season NBA player-performance research platform. Every release must remain
usable, testable, and honest about data freshness.

## Phase 1: Public portfolio release

- [x] Build eight explained dashboard workspaces.
- [x] Add responsive, accessible controls and readable statistical tables.
- [x] Add automated application and calculation tests.
- [x] Prepare GitHub Actions, deployment configuration, and public documentation.
- [x] Add current-season and historical fallback datasets.
- [ ] Publish the GitHub repository.
- [ ] Deploy the interactive application through Streamlit Community Cloud.

## Phase 2: Current-season tracking

- [x] Add a reusable and validated season-update command.
- [x] Preserve compressed raw snapshots outside Git history.
- [x] Calculate team and player rest in versioned processed outputs.
- [x] Generate freshness, record-count, player-count, and team-count metadata.
- [x] Process 2026-27 completed player-game records.
- [x] Configure a daily GitHub Actions refresh.
- [x] Display current-season refresh status without calling it an in-game feed.
- [ ] Add update-failure notifications and stale-data alerts.
- [ ] Add today's schedule before games begin.

## Phase 3: Player news and availability

- [x] Add live player-specific headlines with source and timestamp.
- [x] Add hourly caching and manual refresh.
- [x] Separate official, injury-related, and general headline labels.
- [ ] Ingest official NBA injury reports as structured records.
- [ ] Match availability records using stable player identifiers.
- [ ] Preserve the time each status was first observed.
- [ ] Add expected-minutes and role estimates without automatically trusting a
  headline.

## Phase 4: Forecasting improvements

- [x] Build a chronological recent-form baseline.
- [x] Compare it with a simple rest-aware model.
- [x] Report Brier score, log loss, calibration context, and sample size.
- [x] Add transparent expected-minutes and manual scenarios.
- [ ] Add opponent defense, venue, pace, travel, and recent-workload features.
- [ ] Add teammate availability and projected-role features.
- [ ] Add prediction intervals and sample-quality indicators.
- [ ] Maintain historical training data separately from current-season scoring.

## Phase 5: Advanced differentiators

- **What changed panel:** summarize new games, status changes, and corrected rows
  after every refresh.
- **Travel fatigue index:** combine distance, time-zone changes, altitude, and
  consecutive road games.
- **Role opportunity map:** estimate minutes and usage changes when teammates are
  unavailable.
- **Uncertainty meter:** place confidence intervals and sample-quality warnings
  beside every estimate.
- **Model drift monitor:** detect when current-season performance stops resembling
  the historical training period.
- **WNBA extension:** reuse the data contracts and dashboard structure for the
  sport most directly aligned with the internship's summer calendar.

## Product principles

- Never fabricate injuries, news, model performance, or live status.
- Display source and timestamp for every current-season or news item.
- Label daily completed-game tracking separately from real-time in-game data.
- Keep descriptive history, scenario assumptions, and model forecasts visually
  distinct.
- Never expose API keys in GitHub, application logs, or downloadable files.
- Stop on ambiguous data rather than silently selecting a convenient value.
- Prefer delayed, reliable updates over unsupported claims of live coverage.

