"""Discord guild incidents data model."""

from __future__ import annotations

from datetime import datetime

from wd_discord.models import DiscordModel


class IncidentsData(DiscordModel):
    """https://docs.discord.com/developers/resources/guild#incidents-data-object."""

    invites_disabled_until: datetime | None
    """When invites get enabled again."""
    dms_disabled_until: datetime | None
    """When direct messages get enabled again."""
    dm_spam_detected_at: datetime | None = None
    """When the dm spam was detected."""
    raid_detected_at: datetime | None = None
    """When the raid was detected."""
