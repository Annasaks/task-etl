-- One table per source; same structure both sides.

CREATE TABLE IF NOT EXISTS teams_api_sports (
    team_id          VARCHAR(50)  NOT NULL,
    team_name        VARCHAR(100) NOT NULL,
    founded_year     SMALLINT,
    logo_url         TEXT,
    stadium_name     VARCHAR(100),
    stadium_city     VARCHAR(100),
    stadium_capacity INTEGER,
    league_position  SMALLINT,
    points           SMALLINT,
    wins             SMALLINT,
    draws            SMALLINT,
    losses           SMALLINT,
    goals_for        SMALLINT,
    goals_against    SMALLINT,
    source_api       VARCHAR(20)  NOT NULL DEFAULT 'api_sports',
    season           SMALLINT     NOT NULL,
    snapshot_at      TIMESTAMP    NOT NULL,
    extra_fields     TEXT,
    PRIMARY KEY (team_id, snapshot_at)
);

CREATE TABLE IF NOT EXISTS teams_api_football (
    team_id          VARCHAR(50)  NOT NULL,
    team_name        VARCHAR(100) NOT NULL,
    founded_year     SMALLINT,
    logo_url         TEXT,
    stadium_name     VARCHAR(100),
    stadium_city     VARCHAR(100),
    stadium_capacity INTEGER,
    league_position  SMALLINT,
    points           SMALLINT,
    wins             SMALLINT,
    draws            SMALLINT,
    losses           SMALLINT,
    goals_for        SMALLINT,
    goals_against    SMALLINT,
    source_api       VARCHAR(20)  NOT NULL DEFAULT 'api_football',
    season           SMALLINT     NOT NULL,
    snapshot_at      TIMESTAMP    NOT NULL,
    extra_fields     TEXT,
    PRIMARY KEY (team_id, snapshot_at)
);

-- One row per (run_id, source_api). Append-only.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id              VARCHAR(20)  NOT NULL,
    source_api          VARCHAR(20)  NOT NULL,
    started_at          TIMESTAMP    NOT NULL,
    ended_at            TIMESTAMP,
    duration_seconds    REAL,
    extract_success     BOOLEAN      NOT NULL,
    transform_success   BOOLEAN      NOT NULL,
    load_success        BOOLEAN      NOT NULL,
    export_success      BOOLEAN      NOT NULL,
    rows_extracted      INTEGER,
    rows_transformed    INTEGER,
    rows_skipped        INTEGER,
    warnings_count      INTEGER,
    errors_count        INTEGER,
    PRIMARY KEY (run_id, source_api)
);
