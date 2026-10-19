"""The partial guild Discord sends inside an interaction (https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object)."""

from __future__ import annotations

from wd_discord.interactions import Locale
from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake


class PartialGuild(DiscordModel):
    """The guild an interaction was sent from: only its ID, preferred locale and features."""

    id: Snowflake
    """Guild ID."""
    locale: Locale
    """The guild's preferred locale."""
    features: list[str]
    """Enabled guild features; kept as strings so features Discord adds later don't fail validation."""
