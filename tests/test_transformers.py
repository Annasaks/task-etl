"""Unit tests for the two transformers — verify they produce the standard schema."""
import json

import pandas as pd

from transform import api_sports, api_football


EXPECTED_COLUMNS = {
    "team_id", "team_name", "founded_year",
    "stadium_name", "stadium_city",
    "league_position", "points", "wins", "draws", "losses",
    "goals_for", "goals_against",
    "source_api", "season", "snapshot_at", "extra_fields",
}


class TestApiSportsTransform:
    def test_returns_dataframe(self, api_sports_teams, api_sports_standings):
        df = api_sports.transform(api_sports_teams, api_sports_standings)
        assert isinstance(df, pd.DataFrame)

    def test_returns_one_row_per_premier_league_team(self, api_sports_teams, api_sports_standings):
        df = api_sports.transform(api_sports_teams, api_sports_standings)
        assert len(df) == 20

    def test_columns_match_standard_schema(self, api_sports_teams, api_sports_standings):
        df = api_sports.transform(api_sports_teams, api_sports_standings)
        assert set(df.columns) == EXPECTED_COLUMNS

    def test_team_id_is_source_prefixed(self, api_sports_teams, api_sports_standings):
        df = api_sports.transform(api_sports_teams, api_sports_standings)
        assert df["team_id"].str.startswith("api_sports_").all()

    def test_returns_none_on_empty_input(self):
        assert api_sports.transform([], []) is None
        assert api_sports.transform(None, None) is None

    def test_extra_fields_captures_unmapped_keys(self, api_sports_teams, api_sports_standings):
        df = api_sports.transform(api_sports_teams, api_sports_standings)
        # API-Sports returns 'form' (last 5 results) which we don't map — must be in extra_fields
        first_extra = json.loads(df.iloc[0]["extra_fields"])
        assert "form" in first_extra


class TestApiFootballTransform:
    def test_returns_dataframe(self, api_football_teams, api_football_standings):
        df = api_football.transform(api_football_teams, api_football_standings)
        assert isinstance(df, pd.DataFrame)

    def test_returns_one_row_per_premier_league_team(self, api_football_teams, api_football_standings):
        df = api_football.transform(api_football_teams, api_football_standings)
        assert len(df) == 20

    def test_columns_match_standard_schema(self, api_football_teams, api_football_standings):
        df = api_football.transform(api_football_teams, api_football_standings)
        assert set(df.columns) == EXPECTED_COLUMNS

    def test_string_numbers_are_cast_to_int(self, api_football_teams, api_football_standings):
        # API-Football returns "76" as a string; the transformer must cast to int.
        df = api_football.transform(api_football_teams, api_football_standings)
        assert pd.api.types.is_integer_dtype(df["points"])
        assert pd.api.types.is_integer_dtype(df["wins"])

    def test_team_id_is_source_prefixed(self, api_football_teams, api_football_standings):
        df = api_football.transform(api_football_teams, api_football_standings)
        assert df["team_id"].str.startswith("api_football_").all()

    def test_extra_fields_captures_coach(self, api_football_teams, api_football_standings):
        # API-Football returns 'coaches' which we don't map — must be in extra_fields
        df = api_football.transform(api_football_teams, api_football_standings)
        first_extra = json.loads(df.iloc[0]["extra_fields"])
        assert "coaches" in first_extra
