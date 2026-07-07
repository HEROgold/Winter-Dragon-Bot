"""Discord emoji model."""

from __future__ import annotations

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake
from wd_discord.user import User


class Emoji(DiscordModel):
    """https://docs.discord.com/developers/resources/emoji#emoji-object."""

    id: Snowflake | None
    """Emoji id."""
    name: str | None
    """Emoji name (can be null only in reaction emoji objects)."""
    roles: list[Snowflake] | None = None
    """Roles allowed to use this emoji."""
    user: User | None = None
    """User that created this emoji."""
    require_colons: bool | None = None
    """Whether this emoji must be wrapped in colons."""
    managed: bool | None = None
    """Whether this emoji is managed."""
    animated: bool | None = None
    """Whether this emoji is animated."""
    available: bool | None = None
    """Whether this emoji can be used, may be false due to loss of Server Boosts."""
