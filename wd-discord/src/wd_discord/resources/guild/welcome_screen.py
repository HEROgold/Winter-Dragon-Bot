"""Discord welcome screen models."""

from __future__ import annotations

lazy from wd_discord.models import DiscordModel
lazy from wd_discord.partial_emoji import PartialEmoji
lazy from wd_discord.snowflake import Snowflake


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
    def emoji(self) -> PartialEmoji | None:
        """Emoji object representing the emoji for this welcome screen channel, or ``None`` if unset."""
        return PartialEmoji.from_fields(self.emoji_id, self.emoji_name)


class WelcomeScreen(DiscordModel):
    """https://docs.discord.com/developers/resources/guild#welcome-screen-object."""

    description: str | None
    """The server description shown in the welcome screen."""
    welcome_channels: list[WelcomeScreenChannel]
    """The channels shown in the welcome screen, up to 5."""
