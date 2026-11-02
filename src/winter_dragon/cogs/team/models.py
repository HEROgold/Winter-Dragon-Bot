"""The team tables: a team and its members, lasting or temporary."""

from datetime import datetime
from enum import StrEnum
lazy from typing import ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import LifecycleModel, Ownership


class TeamKind(StrEnum):
    """Whether a team was drawn for one occasion or is kept."""

    TEMPORARY = "temporary"
    LASTING = "lasting"


class TeamOrigin(StrEnum):
    """How a team came to be."""

    CREATED = "created"
    """Made with ``/team create``."""
    VOICE_SPLIT = "voice split"
    TEXT_SPLIT = "text split"
    SOLO_TOURNAMENT = "solo tournament"


class Team(LifecycleModel, table=True):
    """A group of members, from any guild, apart from any tournament; it belongs to no guild."""

    name: str
    kind: TeamKind
    origin: TeamOrigin
    captain_id: int | None = Field(default=None, sa_type=BigInteger)
    ended_at: datetime | None = Field(default=None, sa_type=AwareDateTime)
    """When a temporary team ended; ``None`` while it lasts, and always for a lasting team."""


class TeamMember(LifecycleModel, table=True):
    """A member of a team, since ``joined_at``; the longest-standing member takes over from a leaving captain."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id")
    natural_key: ClassVar[tuple[str, ...]] = ("team_id", "user_id")

    team_id: int = Field(index=True)
    user_id: int = Field(sa_type=BigInteger, index=True)
    joined_at: datetime = Field(sa_type=AwareDateTime)


TEAM_TABLES = (Team, TeamMember)
