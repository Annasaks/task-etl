from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TeamStanding:
    """Standard schema for a Premier League team + season standings."""

    team_id: str
    team_name: str
    founded_year: Optional[int]
    logo_url: Optional[str]

    stadium_name: Optional[str]
    stadium_city: Optional[str]
    stadium_capacity: Optional[int]

    league_position: Optional[int]
    points: Optional[int]
    wins: Optional[int]
    draws: Optional[int]
    losses: Optional[int]
    goals_for: Optional[int]
    goals_against: Optional[int]

    source_api: str
    season: int
    snapshot_at: datetime
    extra_fields: Optional[str]
