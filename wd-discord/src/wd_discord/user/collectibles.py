"""User collectibles sub-object."""
from __future__ import annotations

lazy from wd_discord.models import DiscordModel
lazy from wd_discord.user.profile import NamePlate


class Collectibles(DiscordModel):
    """https://docs.discord.com/developers/resources/user#collectibles."""

    nameplate: NamePlate | None = None
