import json
import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from config import SEASON
from transform.utils import safe_int, safe_str

logger = logging.getLogger(__name__)

SOURCE = "api_sports"

# Keys we map to typed columns. Anything else goes into extra_fields.
KNOWN_TEAM_KEYS = {"id", "name", "code", "founded", "logo"}
KNOWN_VENUE_KEYS = {"id", "name", "city", "capacity"}
KNOWN_STANDING_KEYS = {"team", "rank", "points", "all", "home", "away", "update"}


def _build_extra(team_block: dict, venue: dict, entry: dict) -> Optional[str]:
    """Collect unmapped fields into a JSON dict so new upstream fields aren't lost."""
    extra = {}
    extra.update({
        f"team.{k}": v for k, v in team_block.items()
        if k not in KNOWN_TEAM_KEYS and v not in (None, "")
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
    """Build a DataFrame matching the standard schema from API-Sports raw responses."""
    if not teams_raw or not standings_raw:
        logger.error(f"{SOURCE}: empty input (teams={bool(teams_raw)}, standings={bool(standings_raw)})")
        return None

    teams_by_id = {t["team"]["id"]: t for t in teams_raw if t.get("team", {}).get("id")}

    snapshot_at = datetime.now(timezone.utc)
    rows = []
    skipped = 0
    warnings = 0

    for entry in standings_raw:
        team_block = entry.get("team", {})
        api_id = team_block.get("id")
        team_name = safe_str(team_block.get("name"))

        if not api_id or not team_name:
            logger.error(f"{SOURCE}: skipping standings entry — missing team id or name: {team_block}")
            skipped += 1
            continue

        team_info = teams_by_id.get(api_id, {})
        team_details = team_info.get("team", {})
        venue = team_info.get("venue", {})

        if not team_info:
            logger.warning(f"{SOURCE}: team {api_id} present in standings but missing in teams endpoint")
            warnings += 1

        all_stats = entry.get("all", {})
        goals = all_stats.get("goals", {})

        row = {
            "team_id": f"{SOURCE}_{api_id}",
            "team_name": team_name,
            "founded_year": safe_int(team_details.get("founded")),
            "logo_url": safe_str(team_details.get("logo") or team_block.get("logo")),
            "stadium_name": safe_str(venue.get("name")),
            "stadium_city": safe_str(venue.get("city")),
            "stadium_capacity": safe_int(venue.get("capacity")),
            "league_position": safe_int(entry.get("rank")),
            "points": safe_int(entry.get("points")),
            "wins": safe_int(all_stats.get("win")),
            "draws": safe_int(all_stats.get("draw")),
            "losses": safe_int(all_stats.get("lose")),
            "goals_for": safe_int(goals.get("for")),
            "goals_against": safe_int(goals.get("against")),
            "source_api": SOURCE,
            "season": SEASON,
            "snapshot_at": snapshot_at,
            "extra_fields": _build_extra(team_details or team_block, venue, entry),
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
    teams = json.loads((raw_dir / "api_sports_teams.json").read_text(encoding="utf-8"))
    standings = json.loads((raw_dir / "api_sports_standings.json").read_text(encoding="utf-8"))
    df = transform(teams, standings)
    if df is not None:
        print(df.to_string(index=False))
