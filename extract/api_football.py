import json
import logging
import requests
from pathlib import Path

from config import API_FOOTBALL_KEY, LEAGUE_ID_API_FOOTBALL, SEASON
from http_utils import retry

logger = logging.getLogger(__name__)

BASE_URL = "https://apiv3.apifootball.com/"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

EXPECTED_TEAM_KEYS = {"team_key", "team_name", "venue"}
EXPECTED_STANDING_KEYS = {
    "team_id", "team_name",
    "overall_league_position", "overall_league_PTS",
    "overall_league_W", "overall_league_D", "overall_league_L",
    "overall_league_GF", "overall_league_GA",
}


def _save_raw(filename: str, data: object) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Raw data saved to {path}")


def _check_schema(sample: dict, expected_keys: set, context: str) -> None:
    missing = expected_keys - set(sample.keys())
    if missing:
        logger.error(f"API-Football schema change in {context}: missing keys {missing}")


@retry(times=3, backoff=2.0)
def _fetch(action: str) -> object:
    response = requests.get(
        BASE_URL,
        params={
            "action": action,
            "league_id": LEAGUE_ID_API_FOOTBALL,
            "season": f"{SEASON}/{SEASON + 1}",
            "APIkey": API_FOOTBALL_KEY,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_teams():
    try:
        data = _fetch("get_teams")
        if isinstance(data, dict) and data.get("error"):
            logger.error(f"API-Football error on get_teams: {data}")
            return None
        if not isinstance(data, list):
            logger.error(f"API-Football schema change: expected list from get_teams, got {type(data).__name__}")
            return None
        if data:
            _check_schema(data[0], EXPECTED_TEAM_KEYS, "get_teams")
        _save_raw("api_football_teams.json", data)
        logger.info(f"API-Football: {len(data)} teams fetched")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"API-Football get_teams request failed permanently: {e}")
        return None


def get_standings():
    try:
        data = _fetch("get_standings")
        if isinstance(data, dict) and data.get("error"):
            logger.error(f"API-Football error on get_standings: {data}")
            return None
        if not isinstance(data, list):
            logger.error(f"API-Football schema change: expected list from get_standings, got {type(data).__name__}")
            return None
        if data:
            _check_schema(data[0], EXPECTED_STANDING_KEYS, "get_standings")
        _save_raw("api_football_standings.json", data)
        logger.info(f"API-Football: {len(data)} standings fetched")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"API-Football get_standings request failed permanently: {e}")
        return None


if __name__ == "__main__":
    from logging_config import setup_logging
    setup_logging()
    teams = get_teams()
    if teams:
        print(json.dumps(teams[0], indent=2))
    standings = get_standings()
    if standings:
        print(json.dumps(standings[0], indent=2))
