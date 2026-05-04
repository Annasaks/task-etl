from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TeamStanding:
    """Standard schema for a Premier League team + season standings.

    Populated from both APIs (API-Sports and API-Football).
    Fields absent in a source are set to None; the transformer logs a WARNING.

    Bonus 2 features:
    - `snapshot_at` : enables historical snapshots (append-only loading).
       Lets downstream consumers track evolution over time — critical for
       AI use cases that depend on temporal signal (e.g. price evolution
       in real estate).
    - `extra_fields` : JSON-encoded dict of API fields not mapped to first-class
       columns. Combined with BigQuery's ALLOW_FIELD_ADDITION, this means new
       upstream fields are captured automatically without breaking the pipeline.
    """

    # --- Team identity ---
    team_id: str               # "{source}_{api_internal_id}", e.g. "api_sports_33"
    team_name: str
    founded_year: Optional[int]
    logo_url: Optional[str]

    # --- Venue ---
    stadium_name: Optional[str]
    stadium_city: Optional[str]
    stadium_capacity: Optional[int]

    # --- Season standings ---
    league_position: Optional[int]
    points: Optional[int]
    wins: Optional[int]
    draws: Optional[int]
    losses: Optional[int]
    goals_for: Optional[int]
    goals_against: Optional[int]

    # --- Pipeline metadata ---
    source_api: str            # "api_sports" | "api_football"
    season: int
    snapshot_at: datetime      # UTC timestamp, set at transform time

    # --- Schema-evolution escape hatch ---
    extra_fields: Optional[str]  # JSON-encoded dict of unmapped upstream fields
