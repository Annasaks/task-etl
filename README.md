# Premier League ETL Pipeline

This pipeline ingests Premier League team and standings data from two football APIs, normalises both sources into a single schema, stores each in its own table or dataset, and exports the result. It runs locally on SQLite or remotely on BigQuery, and is scheduled daily on GitHub Actions.

- Live monitoring dashboard: https://datastudio.google.com/reporting/dab6608e-2856-4583-bd95-2cfd10a9b322
- Scheduled runs: https://github.com/Annasaks/task-etl/actions

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in your API keys
python main.py
python -m scripts.preview     # inspect the loaded tables
```

After a run you will find:

- `data/etl.db` — SQLite database with one table per source plus a metrics table
- `data/exports/*.csv` — one CSV per source
- `logs/etl.log` — pipeline log, cumulative across runs

To run against BigQuery instead of SQLite:

```bash
LOAD_BACKEND=bigquery python main.py
```

## Architecture

```
                       main.py
                          |
              +-----------+-----------+
              |                       |
        API-Sports flow         API-Football flow
        extract -> transform    extract -> transform
        -> load -> CSV          -> load -> CSV
              |                       |
        teams_api_sports        teams_api_football
```

The two sources run as independent flows. A failure on one does not stop the other. They share only the column structure of the standard schema, never the data: each source lands in its own SQLite table or its own BigQuery dataset.

## Standard schema

12 business columns plus 4 technical (lineage and history). The full DDL is in [`schema.sql`](schema.sql).

| Field | Type | Source |
| --- | --- | --- |
| `team_id` | STRING | both, prefixed by source (`api_sports_50`) |
| `team_name` | STRING | both |
| `founded_year` | INTEGER | teams |
| `stadium_name`, `stadium_city` | STRING | teams.venue |
| `league_position`, `points` | INTEGER | standings |
| `wins`, `draws`, `losses` | INTEGER | standings |
| `goals_for`, `goals_against` | INTEGER | standings |
| `source_api`, `season` | STRING / INT | pipeline metadata |
| `snapshot_at` | TIMESTAMP | append-only history |
| `extra_fields` | STRING (JSON) | catch-all for upstream fields not mapped to typed columns |

**Why these fields.** All eight fields explicitly listed in the PDF are present (team name, foundation year, home stadium, city, table position, wins, losses, goals scored). I added the complements without which the data is incomplete: `draws` to close the W-D-L triplet, `goals_against` to make the goal differential computable, `points` because it is the actual ranking metric in football. `team_id` is the technical primary key, prefixed by source so the same team across the two APIs cannot collide (Manchester City is `50` on API-Sports and `80` on API-Football). `source_api` and `season` give lineage and scope. `snapshot_at` and `extra_fields` come from Bonus 2.

I deliberately left out a few fields the APIs return: `team_code` is only available on API-Sports (would leave a half-empty column), `team_country` is constant for a single league (always "England"), `played` and `goals_diff` are computable from other columns, and the home/away splits are too granular for a team summary — they land in `extra_fields` if they are needed later.

## The two APIs

| | API-Sports | API-Football |
| --- | --- | --- |
| Auth | `x-apisports-key` header | `APIkey` query param |
| Format | nested JSON | flat keys |
| Numeric types | native ints | strings (cast in transformer) |

Each API has its own transformer; there is no shared parser. Both produce the same standard schema, but the mapping logic is per-source.

For each source, the transformer joins `teams` and `standings` (the schema needs both) using a Python dict-lookup on the team identifier. I chose this over `pd.merge` because the volume is small (20 teams) and the JSON is nested — a dict lookup is direct, fast and easier to read.

**One mismatch is documented.** API-Sports correctly returns the 2023/24 final standings. API-Football's free tier ignores the `season` parameter and returns the current season instead. The PDF accepts this case explicitly: *"if you cannot get full seasonal data / misaligning seasons due to limits, that is acceptable."* The two tables remain independent, so there is no cross-contamination — only a divergence that is documented rather than hidden.

## Error handling

The pipeline distinguishes three severities and applies them consistently across the codebase.

| Concern | Behaviour | File |
| --- | --- | --- |
| Optional field missing | `WARNING` logged, `None` written, row kept | `transform/api_*.py` |
| Critical field missing (`team_id` or `team_name`) | `ERROR` logged, row skipped | `transform/api_*.py` |
| Network timeout, 5xx, 429 | retry three times with exponential backoff (2s, 4s, 8s) | `http_utils.py` |
| Permanent HTTP error (4xx) | no retry, source skipped, the other source continues | `extract/api_*.py` |
| Unexpected response shape | expected keys compared against received keys, `ERROR` logged with the diff | `extract/api_*.py:_check_schema` |

Logs are written to both `logs/etl.log` (cumulative) and stdout. Each transform ends with a summary line `transformed N rows, M skipped, K warnings`, and the pipeline ends with `API-Sports: 20 rows / loaded / CSV ok / 1.5s`.

## Tech choices

I chose Python with pandas because the source data is nested JSON and the volume is small (20 rows per source); a SQL-based ELT would have been heavier than what the data needs. SQLAlchemy provides the SQLite engine, which means swapping in PostgreSQL would only be a connection-string change. For BigQuery I use the official `google-cloud-bigquery` client, which integrates with Application Default Credentials in dev and with a service account in CI.

The dispatcher pattern in `load/loader.py` lets `LOAD_BACKEND` toggle between SQLite and BigQuery without any branching in `main.py`. The same code path runs locally and in production.

For the schedule, I used GitHub Actions rather than Cloud Run or Cloud Functions because I wanted no Docker, the cron to live next to the code, and the runs to be directly visible to anyone reviewing the project.

## Bonuses

### Monitoring dashboard

Live: https://datastudio.google.com/reporting/dab6608e-2856-4583-bd95-2cfd10a9b322

Each run writes per-source metrics — duration, success flags, row counts, warnings, errors — to a `pipeline_monitoring.pipeline_runs` table on BigQuery. The Looker Studio dashboard reads this table and shows pipeline health (KPI scorecards, time series, error counts) alongside a top-5 business chart that reads from the data table. Implementation in [`monitoring/`](monitoring/).

### Schema evolution and historical snapshots

The data tables are loaded in append mode rather than truncated, so each run adds 20 new rows per source tagged with `snapshot_at` (set at transform time). The same team can therefore appear in multiple rows over time, which is what enables temporal queries such as "how have Manchester City's points evolved week over week".

For the schema-evolution side, every transformer collects upstream fields that aren't mapped to typed columns into a JSON-encoded `extra_fields` dict. No upstream field is dropped. On BigQuery, the load job uses `schema_update_options=[ALLOW_FIELD_ADDITION]`, so promoting a captured field to a first-class column is one line in the transformer plus the next run — no manual table migration.

### Scheduled execution

The workflow `.github/workflows/etl.yml` runs daily at 06:00 UTC and is also manually triggerable. It authenticates to GCP via a service account stored as a GitHub Secret, runs the pipeline against BigQuery, and uploads the logs and CSVs as run artifacts (kept 14 days).

## Project layout

```
extract/     REST API clients, one per source (retry, schema check, raw JSON dump)
transform/   raw response -> standard schema, one per source
load/        backend dispatcher (SQLite or BigQuery)
export/      CSV writer
monitoring/  per-run metrics collection
main.py      orchestrator
schema.sql   formal DDL
```

## Task coverage

| Requirement | Status |
| --- | --- |
| Fetch from both APIs (teams + standings) | done |
| Single standard schema (around 10–15 fields) | done — 18 fields, justified above |
| Two separate source flows, separate tables/datasets | done |
| Error logging (missing fields, timeouts, schema changes) | done |
| GCP / BigQuery | done |
| CSV export | done |
| Optional — scheduled execution | done (GitHub Actions, daily) |
| Bonus — monitoring dashboard | done (Looker Studio) |
| Bonus — schema evolution and snapshots | done |
