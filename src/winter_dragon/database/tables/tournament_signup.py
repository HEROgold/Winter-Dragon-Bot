"""Database tables for tournament signup and registration."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, ForeignKey
from sqlmodel import Field, SQLModel

from winter_dragon.database.keys import get_foreign_key


class TournamentSignupConfig(SQLModel, table=True):
    """Guild-specific signup configuration."""

    id: int = Field(sa_type=BigInteger, primary_key=True, index=True, unique=True)
    announcement_channel_id: int | None = Field(sa_type=BigInteger, default=None)
    tournament_voice_channel_id: int | None = Field(sa_type=BigInteger, default=None)


class TournamentSignupEvent(SQLModel, table=True):
    """Stores a tournament scheduled event and its signup announcement."""

    id: int | None = Field(default=None, primary_key=True, index=True)
    guild_id: int = Field(sa_type=BigInteger, index=True)
    scheduled_event_id: int = Field(sa_type=BigInteger, index=True, unique=True)
    announce_message_id: int | None = Field(sa_type=BigInteger, default=None)
    location_id: int | None = Field(sa_type=BigInteger, default=None)
    event_name: str | None = Field(default=None)
    event_description: str | None = Field(default=None)
    start_time: datetime | None = Field(default=None)
    reminder_one_day_sent: bool = Field(default=False)
    reminder_two_hour_sent: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TournamentSignupParticipant(SQLModel, table=True):
    """Tracks players who joined a tournament signup."""

    id: int | None = Field(default=None, primary_key=True, index=True)
    event_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey(get_foreign_key(TournamentSignupEvent)), nullable=False),
        index=True,
    )
    user_id: int = Field(sa_type=BigInteger, index=True)
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
