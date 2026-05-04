import json
import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from config import SEASON

logger = logging.getLogger(__name__)

SOURCE = "api_football"

# Source columns we map to schema columns. Anything else goes to extra_fields.
MAPPED_COLS = {
    "team_id", "team_name", "team_key",
    "team_founded", "team_badge",
    "venue.venue_name", "venue.venue_city", "venue.venue_capacity",
    "overall_league_position", "overall_league_PTS",
    "overall_league_W", "overall_league_D", "overall_league_L",
    "overall_league_GF", "overall_league_GA",
    # technical fields we don't want to clutter extra_fields with:
    "country_name", "league_id", "league_name",
}


def transform(teams_raw: list, standings_raw: list) -> Optional[pd.DataFrame]:
    if not teams_raw or not standings_raw:
        logger.error(f"{SOURCE}: empty input")
        return None

    # 1. Flatten. Drop "players" list before normalising — too large, not team-level.
    teams_clean = [{k: v for k, v in t.items() if k != "players"} for t in teams_raw]
    teams = pd.json_normalize(teams_clean)
    standings = pd.json_normalize(standings_raw)

    # 2. Join standings (main) with teams (enrichment) on the team key.
    # API-Football names it "team_id" in standings and "team_key" in teams.
    df = standings.merge(
        teams, left_on="team_id", right_on="team_key", how="left", suffixes=("", "_t")
    )

    # 3. Drop rows missing critical fields
    initial = len(df)
    df = df.dropna(subset=["team_id", "team_name"])
    skipped = initial - len(df)
    if skipped:
        logger.error(f"{SOURCE}: skipped {skipped} rows missing team_id/team_name")

    # 4. Map source columns to the standard schema
    out = pd.DataFrame({
        "team_id": SOURCE + "_" + df["team_id"].astype(str),
        "team_name": df["team_name"],
        "founded_year": pd.to_numeric(df.get("team_founded"), errors="coerce").astype("Int64"),
        "logo_url": df.get("team_badge_t").fillna(df.get("team_badge")),
        "stadium_name": df.get("venue.venue_name"),
        "stadium_city": df.get("venue.venue_city"),
        "stadium_capacity": pd.to_numeric(df.get("venue.venue_capacity"), errors="coerce").astype("Int64"),
        "league_position": pd.to_numeric(df["overall_league_position"], errors="coerce").astype("Int64"),
        "points": pd.to_numeric(df["overall_league_PTS"], errors="coerce").astype("Int64"),
        "wins": pd.to_numeric(df["overall_league_W"], errors="coerce").astype("Int64"),
        "draws": pd.to_numeric(df["overall_league_D"], errors="coerce").astype("Int64"),
        "losses": pd.to_numeric(df["overall_league_L"], errors="coerce").astype("Int64"),
        "goals_for": pd.to_numeric(df["overall_league_GF"], errors="coerce").astype("Int64"),
        "goals_against": pd.to_numeric(df["overall_league_GA"], errors="coerce").astype("Int64"),
        "source_api": SOURCE,
        "season": SEASON,
        "snapshot_at": datetime.now(timezone.utc),
    })

    # 5. Pack unmapped columns into extra_fields
    out["extra_fields"] = _build_extra(df)

    # 6. Warn on missing critical numeric fields
    for col in ("league_position", "points", "wins", "draws", "losses", "goals_for", "goals_against"):
        n_missing = out[col].isna().sum()
        if n_missing:
            logger.warning(f"{SOURCE}: {n_missing} rows missing '{col}'")

    logger.info(f"{SOURCE}: transformed {len(out)} rows, {skipped} skipped")
    return out


def _build_extra(df: pd.DataFrame) -> pd.Series:
    """Pack columns not in MAPPED_COLS into a JSON-encoded string per row."""
    extra_cols = [c for c in df.columns if c not in MAPPED_COLS and not c.endswith("_t")]
    if not extra_cols:
        return pd.Series([None] * len(df), index=df.index)

    def to_json(row):
        d = {k: v for k, v in row.dropna().items() if v != ""}
        return json.dumps(d, ensure_ascii=False, default=str) if d else None

    return df[extra_cols].apply(to_json, axis=1)


if __name__ == "__main__":
    from pathlib import Path
    logging.basicConfig(level=logging.INFO)
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    teams = json.loads((raw_dir / "api_football_teams.json").read_text(encoding="utf-8"))
    standings = json.loads((raw_dir / "api_football_standings.json").read_text(encoding="utf-8"))
    df = transform(teams, standings)
    if df is not None:
        print(df.to_string(index=False))
