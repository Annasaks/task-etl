# Premier League ETL Pipeline

A modular ETL pipeline that fetches Premier League team and standings data from **two independent football APIs**, normalises them into a single standard schema, stores each source in its own dataset, and exports to CSV. Runs locally (SQLite) or in the cloud (BigQuery), and is scheduled daily via GitHub Actions.

> Home task assignment: see the original brief in [the task description](#task-coverage).

---

## Quick start

### Run locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy .env.example to .env and fill in your API keys
cp .env.example .env
# edit .env

# 3. Run the full pipeline (extract → transform → load → export)
python main.py

# 4. Inspect the loaded data
python -m scripts.preview
```

After running, you'll find:
- `data/raw/*.json` — raw API responses (4 files)
- `data/etl.db` — SQLite database with 2 tables
- `data/exports/*.csv` — CSV export per source (2 files)
- `logs/etl.log` — pipeline log

### Run against BigQuery

```bash
# Set the backend in .env or as an env var
LOAD_BACKEND=bigquery python main.py
```

The pipeline will write to two separate datasets in your GCP project (configured in `.env`).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                            main.py                                   │
│                                                                      │
│  ┌───────────┐    ┌────────────┐    ┌───────────┐    ┌──────────┐  │
│  │  EXTRACT  │ →  │ TRANSFORM  │ →  │   LOAD    │ →  │  EXPORT  │  │
│  │ (REST API)│    │  (pandas)  │    │ (SQLite / │    │  (CSV)   │  │
│  │           │    │            │    │  BigQuery)│    │          │  │
│  └───────────┘    └────────────┘    └───────────┘    └──────────┘  │
│                                                                      │
│   Two independent flows, one per source — failure of one does not   │
│   stop the other. Each source ends up in its own dataset/table.     │
└─────────────────────────────────────────────────────────────────────┘
```

**Source flow A** — `API-Sports` → table `teams_api_sports` (or BigQuery dataset `api_sports_data.teams`)
**Source flow B** — `API-Football` → table `teams_api_football` (or BigQuery dataset `api_football_data.teams`)

The two sources never mix. They share only the **standard schema** (the column structure), not the data.

---

## Standard schema (16 fields)

Defined in [`schema.py`](schema.py) (Python dataclass — runtime contract) and [`schema.sql`](schema.sql) (SQL DDL — formal definition).

| Field | Type | Source endpoint | Why |
|---|---|---|---|
| `team_id` | STRING | both | Source-prefixed primary key (`api_sports_50` / `api_football_80`) — avoids collisions across sources |
| `team_name` | STRING | both | PDF requirement: "team name" |
| `founded_year` | INTEGER | teams | PDF requirement: "foundation year" |
| `logo_url` | STRING | teams | Useful for downstream dashboards |
| `stadium_name` | STRING | teams.venue | PDF requirement: "home stadium" |
| `stadium_city` | STRING | teams.venue | PDF requirement: "city" |
| `stadium_capacity` | INTEGER | teams.venue | Useful analytics dimension |
| `league_position` | INTEGER | standings | PDF requirement: "table position" |
| `points` | INTEGER | standings | Implied by performance |
| `wins` | INTEGER | standings | PDF requirement: "wins" |
| `draws` | INTEGER | standings | Logical complement |
| `losses` | INTEGER | standings | PDF requirement: "losses" |
| `goals_for` | INTEGER | standings | PDF requirement: "goals scored" |
| `goals_against` | INTEGER | standings | Logical complement |
| `source_api` | STRING | metadata | Lineage |
| `season` | INTEGER | metadata | Lineage |

### Schema design choices

- **16 fields** — slightly above the PDF's "around 10–15" range. The justification: `logo_url`, `stadium_capacity`, `draws`, `goals_against` enable richer downstream analytics (and are kept symmetric across both sources).
- **`team_code` was dropped** — present only in API-Sports, absent in API-Football. Including it would have left a half-empty column. Removing it makes the schema honest about what both APIs can deliver.
- **All optional fields are `Optional[int]` / `Optional[str]`** — the transformer logs a `WARNING` per missing field rather than crashing.
- **Source-prefixed `team_id`** — the same team has different internal IDs across the two APIs (Manchester City is `50` in API-Sports, `80` in API-Football). Prefixing eliminates any ambiguity.

---

## Data sources

| | API-Sports | API-Football |
|---|---|---|
| Base URL | `https://v3.football.api-sports.io` | `https://apiv3.apifootball.com/` |
| Auth | `x-apisports-key` header | `APIkey` query param |
| Endpoints used | `/teams`, `/standings` | `?action=get_teams`, `?action=get_standings` |
| Premier League ID | `39` | `152` |
| Numeric types | native `int` / `float` | **all strings** (cast to `int` in transformer) |
| Season parameter | `season=2023` (year only) | `season=2023/2024` (slash format) |

### Endpoint structure differences

API-Sports returns nested JSON (`team.id`, `all.goals.for`...). API-Football returns flat keys with prefixes (`team_key`, `overall_league_GF`...). The two transformers handle the mapping per-source — no shared parser.

### Joining teams + standings

Both transformers must combine **two endpoints** to populate the schema:
- `teams` provides identity, founding year, stadium, city
- `standings` provides position, points, wins, draws, losses, goals

The join is done in Python via a dict-lookup (O(n)):
```python
teams_by_id = {t["team"]["id"]: t for t in teams_raw}      # build index
team_info = teams_by_id.get(api_id, {})                    # lookup per row
```

This is preferred over `pd.merge` because the volume is tiny (20 rows) and the JSON is nested — Python is the natural tool to parse it.

---

## Error handling and observability

The PDF requires error logging for: **missing fields**, **API timeouts**, **unexpected schema changes**. Each is addressed:

| Concern | Implementation | Where |
|---|---|---|
| Missing fields (optional) | `WARNING` logged per field, `None` written | `transform/api_*.py` |
| Missing critical fields (`team_id`, `team_name`) | `ERROR` logged, row skipped, count surfaced in summary | `transform/api_*.py` |
| API timeouts | Retry decorator (3 attempts, exponential backoff: 2s/4s/8s) on `Timeout`, `ConnectionError`, HTTP 5xx/408/429 | `http_utils.py` |
| Permanent HTTP errors (4xx) | No retry, `ERROR` logged, source skipped, other source continues | `extract/api_*.py` |
| Unexpected schema changes | Expected key set compared against the first response item, `ERROR` logged with the missing keys | `extract/api_*.py:_check_schema` |
| Pipeline-level failures | Each source has its own try/skip block — a single API outage does not abort the entire pipeline | `main.py:run_source` |

### Logging configuration

- **Both** a file handler (`logs/etl.log`, cumulative) and a stream handler (stdout)
- Format: `timestamp | LEVEL | module | message`
- Three levels are used meaningfully: `INFO` for progress, `WARNING` for recoverable data issues, `ERROR` for unrecoverable failures
- Each transform step logs a summary: `transformed N rows, M skipped, K warnings`

### Verified error scenarios

| Scenario | Outcome |
|---|---|
| Invalid API key (HTTP 403) | No retry, `ERROR` logged, source flow skipped, other source completes |
| Standings entry without `team.id` | `ERROR` logged, row skipped (counted in summary) |
| Team in standings missing from teams endpoint | `WARNING` logged, row kept with `None` for venue fields |
| Missing `venue` key in API-Sports response | `_check_schema` logs `ERROR` with the missing key |

---

## Schema mismatches and known assumptions

### Season alignment between APIs

API-Sports correctly returns the **2023/24 final standings** (Manchester City, 91 pts, 38 games played).
API-Football, on the **free tier**, ignores the `season=2023/2024` parameter and returns the **current season** (Arsenal #1 with 35 games played at fetch time).

This is acknowledged by the PDF:
> *"Stay within the free tier of each API — if you cannot get full seasonal data / misaligning seasons due to limits, that is acceptable."*

The pipeline does not attempt to reconcile this. Each source lands in its own dataset, and the `season` column reflects the **requested** season, not necessarily the season actually returned by the API. This is a known limitation, documented here rather than hidden.

### Field absence

`team_code` exists in API-Sports but not in API-Football. It was removed from the schema to keep the contract symmetric between sources.

### String typing in API-Football

API-Football returns all numeric fields as strings (`"76"`, `"55097"`, `""` for missing). The `transform/utils.py` helpers (`safe_int`, `safe_str`) absorb this without a try/except per call site.

---

## Tech choices and rationale

| Choice | Why |
|---|---|
| **Python + pandas** for transform | Source data is nested JSON, volume is tiny (20 rows × 2 sources) — Python parses naturally and pandas slots into the load step |
| **SQLAlchemy + SQLite** for local load | SQLAlchemy abstracts the engine, so swapping in PostgreSQL would be one URL change. SQLite is in stdlib (zero setup, file-based, easy to inspect) |
| **`google-cloud-bigquery`** for cloud load | Native, well-supported, integrates with ADC for local dev and service accounts for CI |
| **Backend selector via env var** (`LOAD_BACKEND=sqlite\|bigquery`) | Same code path works locally and in production. No conditional branches in `main.py` |
| **One BigQuery dataset per source** | The PDF asks for "dataset OR table" separation — using two datasets is the strictest possible interpretation, with the side benefit of per-source IAM granularity |
| **Pure-Python retry decorator** rather than `tenacity` | One small file, no extra dependency, transparent behaviour |
| **GitHub Actions** for scheduling | No Docker, no Cloud Run setup; the cron lives next to the code; runs are visible to reviewers |

---

## Project structure

```
task-etl/
├── main.py                       # Pipeline orchestrator
├── config.py                     # Centralised env var loading
├── logging_config.py             # File + stdout logging setup
├── http_utils.py                 # @retry decorator
├── schema.py                     # Standard schema (Python dataclass)
├── schema.sql                    # Standard schema (SQL DDL)
├── requirements.txt
├── .env.example                  # Template for .env (real .env is gitignored)
│
├── extract/
│   ├── api_sports.py             # API-Sports HTTP client + schema check
│   └── api_football.py           # API-Football HTTP client + schema check
│
├── transform/
│   ├── utils.py                  # safe_int, safe_str helpers
│   ├── api_sports.py             # API-Sports raw → standard schema
│   └── api_football.py           # API-Football raw → standard schema
│
├── load/
│   ├── loader.py                 # Backend dispatcher
│   ├── sqlite_loader.py          # SQLite backend (default)
│   └── bigquery_loader.py        # BigQuery backend
│
├── export/
│   └── csv_exporter.py           # CSV export per source
│
├── scripts/
│   └── preview.py                # Inspect SQLite content quickly
│
├── .github/workflows/
│   └── etl.yml                   # Daily schedule (06:00 UTC) + manual trigger
│
└── data/
    ├── raw/                      # Raw JSON responses (gitignored)
    ├── etl.db                    # SQLite database (gitignored)
    └── exports/                  # CSV deliverables
```

---

## Configuration reference

All configuration is loaded from `.env` (gitignored) via `python-dotenv`. See `.env.example` for the full list:

```env
# API keys
API_SPORTS_KEY=your_key
API_FOOTBALL_KEY=your_key

# Pipeline scope
LEAGUE_ID_API_SPORTS=39          # Premier League
LEAGUE_ID_API_FOOTBALL=152       # Premier League
SEASON=2023                      # 2023/24 season

# Load backend selector
LOAD_BACKEND=sqlite              # or "bigquery"

# BigQuery config (only used when LOAD_BACKEND=bigquery)
BIGQUERY_PROJECT=task-etlv
BIGQUERY_DATASET_API_SPORTS=api_sports_data
BIGQUERY_DATASET_API_FOOTBALL=api_football_data
BIGQUERY_LOCATION=US
```

---

## Bonus: scheduled execution (GitHub Actions)

The PDF lists scheduling as optional. This pipeline runs **daily at 06:00 UTC** via [`.github/workflows/etl.yml`](.github/workflows/etl.yml), with full BigQuery integration:

```yaml
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:        # also triggerable manually
```

Each run:
1. Authenticates to GCP via a Service Account (stored as a GitHub Secret)
2. Runs the full pipeline against BigQuery
3. Uploads the logs and CSV exports as run artifacts (downloadable for 14 days)

To check the latest run: https://github.com/Annasaks/task-etl/actions

### Required GitHub Secrets
- `GCP_SA_KEY` — service account JSON (with `BigQuery Data Editor` + `BigQuery Job User` + `BigQuery Read Session User`)
- `API_SPORTS_KEY`
- `API_FOOTBALL_KEY`

---

## Task coverage

| PDF requirement | Status | Where |
|---|---|---|
| Fetch from both APIs, teams + standings | ✅ | `extract/api_*.py` |
| Single standard schema (~10–15 fields) | ✅ (16 fields, justified) | `schema.py`, `schema.sql` |
| Two separate source flows | ✅ | `main.py:run_source` × 2 |
| Each source in its own dataset/table | ✅ | SQLite: 2 tables. BigQuery: 2 datasets |
| Error logging — missing fields | ✅ | `transform/*` |
| Error logging — API timeouts | ✅ | `http_utils.py:retry` |
| Error logging — schema changes | ✅ | `extract/*:_check_schema` |
| **Optional** — scheduled execution | ✅ | `.github/workflows/etl.yml` (daily) |
| Export — CSV | ✅ | `data/exports/*.csv` |
| Source code with run instructions | ✅ | this README |
| Schema definition (DDL) | ✅ | `schema.sql` |
| README documentation | ✅ | this file |

---

## Limitations

- **API-Football season filter is not respected on the free tier** — see "Schema mismatches" above. Documented, not hidden.
- **No deduplication** — `WRITE_TRUNCATE` / `if_exists='replace'` means every run replaces the table. There is no historical snapshot. Schema-evolution / versioning would be the natural next step (mentioned as a bonus in the PDF).
- **20 rows per source** is the entire dataset for one Premier League season — not a sample or truncation.
