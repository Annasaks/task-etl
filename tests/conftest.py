"""Shared pytest fixtures."""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def api_sports_teams():
    return _load("api_sports_teams.json")


@pytest.fixture
def api_sports_standings():
    return _load("api_sports_standings.json")


@pytest.fixture
def api_football_teams():
    return _load("api_football_teams.json")


@pytest.fixture
def api_football_standings():
    return _load("api_football_standings.json")
