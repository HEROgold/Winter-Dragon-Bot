"""Tournament database models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship
from winter_dragon.database.extension.model import DiscordID


if TYPE_CHECKING:
    from .tournament_match import TournamentMatch
    from .tournament_player import TournamentPlayer
    from .tournament_spectator import TournamentSpectator
    from .tournament_team import TournamentTeam


class TournamentType(str, Enum):
    """Tournament type enumeration."""

    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"
    ROUND_ROBIN = "round_robin"
    SWISS = "swiss"
    FFA = "ffa"
    RACE = "race"
    GROUP_STAGES = "group_stages"


class TournamentStatus(str, Enum):
    """Tournament status enumeration."""

    PLANNED = "planned"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Tournament(DiscordID, table=True):
    """Tournament model."""

    # name: str = Field(max_length=100)
    # description: str | None = Field(default=None, max_length=1000)
    # tournament_type: TournamentType = Field(default=TournamentType.SINGLE_ELIMINATION)
    # status: TournamentStatus = Field(default=TournamentStatus.PLANNED)
    # guild_id: int = Field(index=True)
    # creator_id: int = Field(index=True)

    # # Tournament configuration
    # max_players: int | None = Field(default=None, ge=2)
    # min_players: int = Field(default=2, ge=2)
    # team_size: int = Field(default=1, ge=1)  # 1 for solo tournaments
    # auto_assign_teams: bool = Field(default=True)

    # # Timing
    # registration_start: datetime | None = Field(default=None)
    # registration_end: datetime | None = Field(default=None)
    # tournament_start: datetime | None = Field(default=None)
    # tournament_end: datetime | None = Field(default=None)

    # # Discord integration
    # category_id: int | None = Field(default=None)  # Main tournament category
    # scoreboard_channel_id: int | None = Field(default=None)
    # announcement_channel_id: int | None = Field(default=None)
    # stage_channel_id: int | None = Field(default=None)  # For spectators

    # # Permission management
    # use_temporary_roles: bool = Field(default=True)
    # participant_role_id: int | None = Field(default=None)
    # spectator_role_id: int | None = Field(default=None)

    # created_at: datetime = Field(default_factory=datetime.utcnow)
    # updated_at: datetime = Field(default_factory=datetime.utcnow)

    # # Relationships
    # players: list[TournamentPlayer] = Relationship(back_populates="tournament")
    # teams: list[TournamentTeam] = Relationship(back_populates="tournament")
    # matches: list[TournamentMatch] = Relationship(back_populates="tournament")
    # spectators: list[TournamentSpectator] = Relationship(back_populates="tournament")
