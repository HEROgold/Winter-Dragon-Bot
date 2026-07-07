"""Forum and voice related models and enums for the Discord Channel object."""
from __future__ import annotations

from enum import IntEnum

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake


class VideoQualityMode(IntEnum):
    """The camera video quality mode of a voice channel."""

    AUTO = 1
    """Discord chooses the quality for optimal performance."""
    FULL = 2
    """720p quality."""


class SortOrderType(IntEnum):
    """The default sort order used to order posts in a forum or media channel."""

    LATEST_ACTIVITY = 0
    """Sort forum posts by activity."""
    CREATION_DATE = 1
    """Sort forum posts by creation time (from most recent to oldest)."""


class ForumLayoutType(IntEnum):
    """The default layout used to display posts in a forum channel."""

    NOT_SET = 0
    """No default has been set for the forum channel."""
    LIST_VIEW = 1
    """Display posts as a list."""
    GALLERY_VIEW = 2
    """Display posts as a collection of tiles."""


class ForumTag(DiscordModel):
    """https://docs.discord.com/developers/resources/channel#forum-tag-object."""

    id: Snowflake
    """Id of the tag."""
    name: str
    """Name of the tag."""
    moderated: bool
    """Whether this tag can only be added to or removed from threads by moderators."""
    emoji_id: Snowflake | None
    """Id of a guild's custom emoji."""
    emoji_name: str | None
    """Unicode character of the emoji."""


class DefaultReaction(DiscordModel):
    """https://docs.discord.com/developers/resources/channel#default-reaction-object."""

    emoji_id: Snowflake | None
    """Id of a guild's custom emoji."""
    emoji_name: str | None
    """Unicode character of the emoji."""
