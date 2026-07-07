"""Discord welcome screen models."""

from __future__ import annotations

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake


class WelcomeScreenChannel(DiscordModel):
    """https://docs.discord.com/developers/resources/guild#welcome-screen-object-welcome-screen-channel-structure."""

    channel_id: Snowflake
    """The channel's id."""
    description: str
    """The description shown for the channel."""
    emoji_id: Snowflake | None
    """The emoji id, if the emoji is custom."""
    emoji_name: str | None
    """The emoji name if custom, the unicode character if standard, or null if no emoji is set."""

    @property
    def emoji(self) -> Emoji | None:
        """Emoji object representing the emoji for this welcome screen channel."""
        # TODO: implement

class WelcomeScreen(DiscordModel):
    """https://docs.discord.com/developers/resources/guild#welcome-screen-object."""

    description: str | None
    """The server description shown in the welcome screen."""
    welcome_channels: list[WelcomeScreenChannel]
    """The channels shown in the welcome screen, up to 5."""
