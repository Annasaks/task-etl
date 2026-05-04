import logging
from typing import Optional

import pandas as pd

from config import SEASON
from transform.utils import safe_int, safe_str

logger = logging.getLogger(__name__)

SOURCE = "api_football"


def transform(teams_raw: list, standings_raw: list) -> Optional[pd.DataFrame]:
    """Build a DataFrame matching the standard schema from API-Football raw responses.

    Joins teams.team_key with standings.team_id (both string-typed by the API).
    Skips rows missing team_id or team_name (logged as ERROR).
    Logs a WARNING per missing optional field.
    All numeric fields are strings in API-Football; safe_int handles casting.
    """
    if not teams_raw or not standings_raw:
        logger.error(f"{SOURCE}: empty input (teams={bool(teams_raw)}, standings={bool(standings_raw)})")
        return None

    teams_by_id = {t.get("team_key"): t for t in teams_raw if t.get("team_key")}

    rows = []
    skipped = 0
    warnings = 0

    for entry in standings_raw:
        api_id = safe_str(entry.get("team_id"))
        team_name = safe_str(entry.get("team_name"))

        if not api_id or not team_name:
            logger.error(f"{SOURCE}: skipping standings entry — missing team id or name: {entry.get('team_name')}")
            skipped += 1
            continue

        team_info = teams_by_id.get(api_id, {})
        venue = team_info.get("venue", {}) if team_info else {}

        if not team_info:
            logger.warning(f"{SOURCE}: team {api_id} present in standings but missing in teams endpoint")
            warnings += 1

        row = {
            "team_id": f"{SOURCE}_{api_id}",
            "team_name": team_name,
            "founded_year": safe_int(team_info.get("team_founded")),
            "logo_url": safe_str(team_info.get("team_badge") or entry.get("team_badge")),
            "stadium_name": safe_str(venue.get("venue_name")),
            "stadium_city": safe_str(venue.get("venue_city")),
            "stadium_capacity": safe_int(venue.get("venue_capacity")),
            "league_position": safe_int(entry.get("overall_league_position")),
            "points": safe_int(entry.get("overall_league_PTS")),
            "wins": safe_int(entry.get("overall_league_W")),
            "draws": safe_int(entry.get("overall_league_D")),
            "losses": safe_int(entry.get("overall_league_L")),
            "goals_for": safe_int(entry.get("overall_league_GF")),
            "goals_against": safe_int(entry.get("overall_league_GA")),
            "source_api": SOURCE,
            "season": SEASON,
        }

        for col, val in row.items():
            if val is None and col not in ("founded_year", "logo_url", "stadium_name", "stadium_city", "stadium_capacity"):
                logger.warning(f"{SOURCE}: team {team_name} missing required-ish field '{col}'")
                warnings += 1

        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"{SOURCE}: transformed {len(df)} rows, {skipped} skipped, {warnings} warnings")
    return df


if __name__ == "__main__":
    import json
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    teams = json.loads((raw_dir / "api_football_teams.json").read_text(encoding="utf-8"))
    standings = json.loads((raw_dir / "api_football_standings.json").read_text(encoding="utf-8"))
    df = transform(teams, standings)
    if df is not None:
        print(df.to_string(index=False))
