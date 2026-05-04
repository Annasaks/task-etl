import json
import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from config import SEASON

logger = logging.getLogger(__name__)

SOURCE = "api_sports"

# Source columns we map to schema columns. Anything else goes to extra_fields.
MAPPED_COLS = {
    "team.id", "team.name", "team.founded", "team.logo",
    "venue.name", "venue.city", "venue.capacity",
    "rank", "points",
    "all.win", "all.draw", "all.lose",
    "all.goals.for", "all.goals.against",
}


def transform(teams_raw: list, standings_raw: list) -> Optional[pd.DataFrame]:
    if not teams_raw or not standings_raw:
        logger.error(f"{SOURCE}: empty input")
        return None

    # 1. Flatten the nested JSON into 2D DataFrames
    standings = pd.json_normalize(standings_raw)
    teams = pd.json_normalize(teams_raw)

    # 2. Join standings (main table) with teams (enrichment) on team.id
    df = standings.merge(teams, on="team.id", how="left", suffixes=("", "_t"))

    # 3. Drop rows missing critical fields
    initial = len(df)
    df = df.dropna(subset=["team.id", "team.name"])
    skipped = initial - len(df)
    if skipped:
        logger.error(f"{SOURCE}: skipped {skipped} rows missing team_id/team_name")

    # 4. Map source columns to the standard schema
    out = pd.DataFrame({
        "team_id": SOURCE + "_" + df["team.id"].astype(int).astype(str),
        "team_name": df["team.name"],
        "founded_year": pd.to_numeric(df.get("team.founded"), errors="coerce").astype("Int64"),
        "logo_url": df.get("team.logo_t").fillna(df.get("team.logo")),
        "stadium_name": df.get("venue.name"),
        "stadium_city": df.get("venue.city"),
        "stadium_capacity": pd.to_numeric(df.get("venue.capacity"), errors="coerce").astype("Int64"),
        "league_position": pd.to_numeric(df["rank"], errors="coerce").astype("Int64"),
        "points": pd.to_numeric(df["points"], errors="coerce").astype("Int64"),
        "wins": pd.to_numeric(df["all.win"], errors="coerce").astype("Int64"),
        "draws": pd.to_numeric(df["all.draw"], errors="coerce").astype("Int64"),
        "losses": pd.to_numeric(df["all.lose"], errors="coerce").astype("Int64"),
        "goals_for": pd.to_numeric(df["all.goals.for"], errors="coerce").astype("Int64"),
        "goals_against": pd.to_numeric(df["all.goals.against"], errors="coerce").astype("Int64"),
        "source_api": SOURCE,
        "season": SEASON,
        "snapshot_at": datetime.now(timezone.utc),
    })

    # 5. Pack unmapped columns into a JSON catch-all
    out["extra_fields"] = _build_extra(df)

    # 6. Warn if any critical column has missing values
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
    teams = json.loads((raw_dir / "api_sports_teams.json").read_text(encoding="utf-8"))
    standings = json.loads((raw_dir / "api_sports_standings.json").read_text(encoding="utf-8"))
    df = transform(teams, standings)
    if df is not None:
        print(df.to_string(index=False))
