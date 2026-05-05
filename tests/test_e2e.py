"""End-to-end test of the ETL pipeline.

Both APIs' `_fetch` functions are mocked to return fixture data; everything
else (transform, load, export, metrics) runs for real against a temp SQLite
DB and a temp exports directory.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from sqlalchemy import create_engine

import main
from extract import api_sports, api_football
from load import sqlite_loader
from export import csv_exporter

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    """Redirect data outputs to a temporary directory."""
    db_path = tmp_path / "etl.db"
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    monkeypatch.setattr(sqlite_loader, "DB_PATH", db_path)
    monkeypatch.setattr(sqlite_loader, "ENGINE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(csv_exporter, "EXPORT_DIR", exports_dir)
    monkeypatch.setattr(api_sports, "RAW_DIR", raw_dir)
    monkeypatch.setattr(api_football, "RAW_DIR", raw_dir)

    import config
    monkeypatch.setattr(config, "LOAD_BACKEND", "sqlite")
    from load import loader
    monkeypatch.setattr(loader, "LOAD_BACKEND", "sqlite")

    return {"db": db_path, "exports": exports_dir}


def test_full_pipeline_with_mocked_apis(isolated_dirs):
    sports_teams = json.loads((FIXTURES / "api_sports_teams.json").read_text(encoding="utf-8"))
    sports_standings = json.loads((FIXTURES / "api_sports_standings.json").read_text(encoding="utf-8"))
    football_teams = json.loads((FIXTURES / "api_football_teams.json").read_text(encoding="utf-8"))
    football_standings = json.loads((FIXTURES / "api_football_standings.json").read_text(encoding="utf-8"))

    # Wrap fixtures in the structure each API actually returns
    def fake_sports_fetch(endpoint):
        if endpoint == "teams":
            return {"response": sports_teams, "errors": []}
        return {"response": [{"league": {"standings": [sports_standings]}}], "errors": []}

    def fake_football_fetch(action):
        return football_teams if action == "get_teams" else football_standings

    with patch.object(api_sports, "_fetch", side_effect=fake_sports_fetch), \
         patch.object(api_football, "_fetch", side_effect=fake_football_fetch):
        main.run_etl()

    # Verify SQLite contents
    engine = create_engine(f"sqlite:///{isolated_dirs['db']}")
    df_sports = pd.read_sql("SELECT * FROM teams_api_sports", engine)
    df_football = pd.read_sql("SELECT * FROM teams_api_football", engine)
    df_metrics = pd.read_sql("SELECT * FROM pipeline_runs", engine)

    assert len(df_sports) == 20
    assert len(df_football) == 20
    assert len(df_metrics) == 2

    # Verify CSV exports
    assert (isolated_dirs["exports"] / "teams_api_sports.csv").exists()
    assert (isolated_dirs["exports"] / "teams_api_football.csv").exists()

    # Verify all metrics rows reflect a successful run
    assert df_metrics["extract_success"].all()
    assert df_metrics["transform_success"].all()
    assert df_metrics["load_success"].all()
    assert df_metrics["export_success"].all()
