"""Configuration settings for the Clash cog."""

from __future__ import annotations

from winter_dragon.config import Config


class ClashSettings:
    """Settings for the Clash cog."""

    riot_api_key = Config("", optional=True)
    """Riot API key for accessing the Clash API."""
