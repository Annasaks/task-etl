import json
import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from config import SEASON
from transform.utils import safe_int, safe_str

logger = logging.getLogger(__name__)

SOURCE = "api_football"

# Top-level keys we map explicitly. Anything else goes into extra_fields.
# We deliberately drop "players" — too large and not a team-level attribute.
KNOWN_TEAM_KEYS = {"team_key", "team_name", "team_country", "team_founded", "team_badge", "venue", "players"}
KNOWN_VENUE_KEYS = {"venue_name", "venue_city", "venue_capacity"}
KNOWN_STANDING_KEYS = {
    "country_name", "league_id", "league_name", "team_id", "team_name", "team_badge",
    "overall_league_position", "overall_league_payed",
    "overall_league_W", "overall_league_D", "overall_league_L",
    "overall_league_GF", "overall_league_GA", "overall_league_PTS",
    # home_*/away_* sub-stats are intentionally captured in extra_fields below.
}


def _build_extra(team_info: dict, venue: dict, entry: dict) -> Optional[str]:
    """Bonus 2B: capture unmapped upstream fields as JSON."""
    extra = {}
    extra.update({
        k: v for k, v in team_info.items()
        if k not in KNOWN_TEAM_KEYS and v not in (None, "", [])
    })
    extra.update({
        f"venue.{k}": v for k, v in venue.items()
        if k not in KNOWN_VENUE_KEYS and v not in (None, "")
    })
    extra.update({
        k: v for k, v in entry.items()
        if k not in KNOWN_STANDING_KEYS and v not in (None, "")
    })
    return json.dumps(extra, ensure_ascii=False) if extra else None


def transform(teams_raw: list, standings_raw: list) -> Optional[pd.DataFrame]:
    """Build a DataFrame matching the standard schema from API-Football raw responses."""
    if not teams_raw or not standings_raw:
        logger.error(f"{SOURCE}: empty input (teams={bool(teams_raw)}, standings={bool(standings_raw)})")
        return None

    teams_by_id = {t.get("team_key"): t for t in teams_raw if t.get("team_key")}

    snapshot_at = datetime.now(timezone.utc)
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
            "snapshot_at": snapshot_at,
            "extra_fields": _build_extra(team_info, venue, entry),
        }

        for col, val in row.items():
            if val is None and col not in (
                "founded_year", "logo_url", "stadium_name", "stadium_city",
                "stadium_capacity", "extra_fields",
            ):
                logger.warning(f"{SOURCE}: team {team_name} missing required-ish field '{col}'")
                warnings += 1

        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"{SOURCE}: transformed {len(df)} rows, {skipped} skipped, {warnings} warnings")
    return df


if __name__ == "__main__":
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    teams = json.loads((raw_dir / "api_football_teams.json").read_text(encoding="utf-8"))
    standings = json.loads((raw_dir / "api_football_standings.json").read_text(encoding="utf-8"))
    df = transform(teams, standings)
    if df is not None:
        print(df.to_string(index=False))
