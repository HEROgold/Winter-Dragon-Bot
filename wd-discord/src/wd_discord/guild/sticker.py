"""Discord sticker models and enums."""

from __future__ import annotations

from enum import IntEnum

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake
from wd_discord.user import User


class StickerType(IntEnum):
    """https://docs.discord.com/developers/resources/sticker#sticker-object-sticker-types."""

    STANDARD = 1
    """An official sticker in a pack."""
    GUILD = 2
    """A sticker uploaded to a guild for the guild's members."""


class StickerFormatType(IntEnum):
    """https://docs.discord.com/developers/resources/sticker#sticker-object-sticker-format-types."""

    PNG = 1
    """PNG sticker format."""
    APNG = 2
    """Animated PNG sticker format."""
    LOTTIE = 3
    """Lottie sticker format."""
    GIF = 4
    """GIF sticker format."""


class Sticker(DiscordModel):
    """https://docs.discord.com/developers/resources/sticker#sticker-object."""

    id: Snowflake
    """Id of the sticker."""
    pack_id: Snowflake | None = None
    """For standard stickers, id of the pack the sticker is from."""
    name: str
    """Name of the sticker."""
    description: str | None
    """Description of the sticker."""
    tags: str
    """Autocomplete/suggestion tags for the sticker (max 200 characters)."""
    type: StickerType
    """Type of sticker."""
    format_type: StickerFormatType
    """Type of sticker format."""
    available: bool | None = None
    """Whether this guild sticker can be used, may be false due to loss of Server Boosts."""
    guild_id: Snowflake | None = None
    """Id of the guild that owns this sticker."""
    user: User | None = None
    """The user that uploaded the guild sticker."""
    sort_value: int | None = None
    """The standard sticker's sort order within its pack."""
