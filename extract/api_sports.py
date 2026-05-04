import json
import logging
import requests
from pathlib import Path

from config import API_SPORTS_KEY, LEAGUE_ID_API_SPORTS, SEASON
from http_utils import retry

logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_SPORTS_KEY}
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

EXPECTED_TEAM_KEYS = {"team", "venue"}
EXPECTED_TEAM_INNER = {"id", "name"}
EXPECTED_STANDING_KEYS = {"rank", "team", "points", "all"}


def _save_raw(filename: str, data: object) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Raw data saved to {path}")


def _check_schema(sample: dict, expected_keys: set, context: str) -> None:
    missing = expected_keys - set(sample.keys())
    if missing:
        logger.error(f"API-Sports schema change in {context}: missing keys {missing}")


@retry(times=3, backoff=2.0)
def _fetch(endpoint: str) -> dict:
    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers=HEADERS,
        params={"league": LEAGUE_ID_API_SPORTS, "season": SEASON},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_teams():
    try:
        data = _fetch("teams")
        if data.get("errors"):
            logger.error(f"API-Sports errors on /teams: {data['errors']}")
            return None
        teams = data.get("response", [])
        if teams:
            _check_schema(teams[0], EXPECTED_TEAM_KEYS, "/teams")
            inner = teams[0].get("team", {})
            _check_schema(inner, EXPECTED_TEAM_INNER, "/teams[].team")
        _save_raw("api_sports_teams.json", teams)
        logger.info(f"API-Sports: {len(teams)} teams fetched")
        return teams
    except requests.exceptions.RequestException as e:
        logger.error(f"API-Sports /teams request failed permanently: {e}")
        return None


def get_standings():
    try:
        data = _fetch("standings")
        if data.get("errors"):
            logger.error(f"API-Sports errors on /standings: {data['errors']}")
            return None
        try:
            standings = data["response"][0]["league"]["standings"][0]
        except (KeyError, IndexError) as e:
            logger.error(f"API-Sports schema change detected in /standings nesting: {e}")
            return None
        if standings:
            _check_schema(standings[0], EXPECTED_STANDING_KEYS, "/standings")
        _save_raw("api_sports_standings.json", standings)
        logger.info(f"API-Sports: {len(standings)} standings fetched")
        return standings
    except requests.exceptions.RequestException as e:
        logger.error(f"API-Sports /standings request failed permanently: {e}")
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
