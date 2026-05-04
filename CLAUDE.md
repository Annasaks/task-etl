# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Objective (home task)

Build a modular ETL pipeline that fetches Premier League team + standings data from **two APIs**, normalises them into a **single standard schema**, stores each source separately, and exports the result. GCP (BigQuery) is preferred for storage.

**APIs:**
- API-Sports v3 — `https://v3.football.api-sports.io` — Premier League `league_id=39`
- API-Football — `https://apifootball.com/documentation/` — separate key

**Deliverables required:** source code, schema DDL, README with design decisions, exported dataset (CSV or REST API).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full ETL pipeline
python main.py

# Test a single extract module in isolation
python -m extract.api_sports
python -m extract.api_football
```

## Architecture

Two parallel extract → transform flows that both converge on a shared standard schema, then load into separate tables.

```
extract/api_sports.py   →  transform/api_sports_transformer.py   →  load/ (table: teams_api_sports)
extract/api_football.py →  transform/api_football_transformer.py →  load/ (table: teams_api_football)
```

- **`extract/api_sports.py`** — fetches `/teams` and `/standings` from API-Sports. Includes retry logic and structured logging.
- **`extract/api_football.py`** — fetches equivalent endpoints from API-Football.
- **`transform/api_sports_transformer.py`** — maps API-Sports raw response → standard schema.
- **`transform/api_football_transformer.py`** — maps API-Football raw response → standard schema.
- **`load/loader.py`** — writes DataFrames to BigQuery (or CSV fallback). Keeps the two sources in separate tables.
- **`main.py`** — orchestrates both flows sequentially; one failure does not abort the other.

## Standard schema (10-13 fields)

| Field | Type | Source |
|---|---|---|
| `team_id` | STRING | API internal id (prefixed by source) |
| `team_name` | STRING | teams endpoint |
| `team_code` | STRING | teams endpoint |
| `founded_year` | INTEGER | teams endpoint |
| `stadium_name` | STRING | teams/venue endpoint |
| `stadium_city` | STRING | teams/venue endpoint |
| `stadium_capacity` | INTEGER | teams/venue endpoint |
| `league_position` | INTEGER | standings endpoint |
| `points` | INTEGER | standings endpoint |
| `wins` | INTEGER | standings endpoint |
| `draws` | INTEGER | standings endpoint |
| `losses` | INTEGER | standings endpoint |
| `goals_for` | INTEGER | standings endpoint |
| `goals_against` | INTEGER | standings endpoint |
| `source_api` | STRING | pipeline metadata |

## Configuration

All credentials loaded from `.env` via `python-dotenv` in `config.py`. The `.env` is gitignored.

| Variable | Purpose |
|---|---|
| `API_SPORTS_KEY` | API-Sports auth header `x-apisports-key` |
| `LEAGUE_ID_API_SPORTS` | `39` for Premier League |
| `SEASON` | e.g. `2024` |
| `API_FOOTBALL_KEY` | API-Football auth token |
| `LEAGUE_ID_API_FOOTBALL` | API-Football Premier League id |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON (BigQuery) |
| `BIGQUERY_PROJECT` | GCP project id |
| `BIGQUERY_DATASET` | BigQuery dataset name |

## Error handling conventions

- All extract functions return `None` on failure (never raise) and log via `logging.getLogger(__name__)`.
- Transform functions log a `WARNING` per missing field and fill with `None`; they log an `ERROR` and return `None` for unrecoverable rows.
- The load step logs record counts on success and raises on fatal write errors.
- A top-level `logs/etl.log` file captures all pipeline runs.
