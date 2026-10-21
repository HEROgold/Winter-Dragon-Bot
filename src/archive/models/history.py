"""What happened, appended and never changed; ``created_at`` is when the archive received it."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field

from archive.models.base import ArchiveEvent, json_column, moment, snowflake
from archive.models.children import Activity


class GatewayEvent(ArchiveEvent, table=True):
    """A raw event: one dispatch exactly as Discord sent it, kept for a limited number of days."""

    name: str = Field(index=True)
    sequence: int | None = None
    guild_id: int | None = snowflake(index=True)
    payload: dict[str, Any] | None = json_column()


class PresenceUpdate(ArchiveEvent, table=True):
    """A user's status and activities in a guild, from a PRESENCE_UPDATE or a snapshot."""

    children: ClassVar = {"activities": Activity}

    source: str
    """The event the presence came from: PRESENCE_UPDATE, or GUILD_CREATE / GUILD_MEMBERS_CHUNK for a snapshot."""
    guild_id: int | None = snowflake(index=True)
    user_id: int | None = snowflake(index=True)
    status: str | None = None
    client_status_desktop: str | None = None
    client_status_mobile: str | None = None
    client_status_web: str | None = None
    client_status_vr: str | None = None


class VoiceStateUpdate(ArchiveEvent, table=True):
    """A user's voice connection in a guild, from a VOICE_STATE_UPDATE or a snapshot."""

    source: str
    """The event the voice state came from: VOICE_STATE_UPDATE, or GUILD_CREATE for a snapshot."""
    guild_id: int | None = snowflake(index=True)
    channel_id: int | None = snowflake(index=True)
    """The voice channel; ``None`` when the user left voice."""
    user_id: int | None = snowflake(index=True)
    session_id: str | None = None
    deaf: bool | None = None
    mute: bool | None = None
    self_deaf: bool | None = None
    self_mute: bool | None = None
    self_stream: bool | None = None
    self_video: bool | None = None
    suppress: bool | None = None
    request_to_speak_timestamp: datetime | None = moment()


class TypingStart(ArchiveEvent, table=True):
    """A user started typing in a channel."""

    channel_id: int | None = snowflake(index=True)
    guild_id: int | None = snowflake(index=True)
    user_id: int | None = snowflake(index=True)
    timestamp: int | None = Field(default=None, sa_type=BigInteger)
    """When they started typing, in Unix seconds."""


class ReactionEvent(ArchiveEvent, table=True):
    """A reaction added to or removed from a message, or a message's reactions cleared."""

    action: str
    """``add``, ``remove``, ``remove_all`` or ``remove_emoji``."""
    message_id: int | None = snowflake(index=True)
    channel_id: int | None = snowflake()
    guild_id: int | None = snowflake(index=True)
    user_id: int | None = snowflake(index=True)
    message_author_id: int | None = snowflake()
    emoji_id: int | None = snowflake()
    emoji_name: str | None = None
    emoji_animated: bool | None = None
    burst: bool | None = None
    """Whether it is a super reaction."""
    type: int | None = None


class MessageRevision(ArchiveEvent, table=True):
    """A message's content after one of its edits."""

    message_id: int = Field(sa_type=BigInteger, index=True)
    channel_id: int | None = snowflake()
    guild_id: int | None = snowflake()
    content: str | None = None
    edited_timestamp: datetime | None = moment()


class ChannelPinsUpdate(ArchiveEvent, table=True):
    """A message was pinned or unpinned in a channel."""

    guild_id: int | None = snowflake()
    channel_id: int | None = snowflake(index=True)
    last_pin_timestamp: datetime | None = moment()


class InteractionEvent(ArchiveEvent, table=True):
    """An interaction sent to the archive's application."""

    discord_id: int | None = snowflake()
    type: int | None = None
    application_id: int | None = snowflake()
    guild_id: int | None = snowflake(index=True)
    channel_id: int | None = snowflake()
    locale: str | None = None
