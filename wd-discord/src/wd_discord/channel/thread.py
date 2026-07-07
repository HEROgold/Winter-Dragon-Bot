"""Thread metadata and member models for the Discord Channel object."""
from __future__ import annotations

from datetime import datetime

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake


class ThreadMetadata(DiscordModel):
    """https://docs.discord.com/developers/resources/channel#thread-metadata-object."""

    archived: bool
    """Whether the thread is archived."""
    auto_archive_duration: int
    """Duration in minutes to automatically archive the thread after recent activity."""
    archive_timestamp: datetime
    """Timestamp when the thread's archive status was last changed."""
    locked: bool
    """Whether the thread is locked."""
    invitable: bool | None = None
    """Whether non-moderators can add other non-moderators to a private thread."""
    create_timestamp: datetime | None = None
    """Timestamp when the thread was created; only populated for threads created after 2022-01-09."""


class ThreadMember(DiscordModel):
    """https://docs.discord.com/developers/resources/channel#thread-member-object.

    The nested guild ``member`` object is intentionally omitted as it is out of scope.
    """

    id: Snowflake | None = None
    """Id of the thread."""
    user_id: Snowflake | None = None
    """Id of the user."""
    join_timestamp: datetime
    """Timestamp when the user last joined the thread."""
    flags: int
    """User-thread settings, currently only used for notifications."""
