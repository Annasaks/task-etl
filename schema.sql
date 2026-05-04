-- Standard schema for Premier League team standings
-- One table per source API; same structure for both.

CREATE TABLE IF NOT EXISTS teams_api_sports (
    team_id          VARCHAR(50)  PRIMARY KEY,   -- "api_sports_{id}"
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
    season           SMALLINT     NOT NULL
);

CREATE TABLE IF NOT EXISTS teams_api_football (
    team_id          VARCHAR(50)  PRIMARY KEY,   -- "api_football_{id}"
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
    season           SMALLINT     NOT NULL
);
