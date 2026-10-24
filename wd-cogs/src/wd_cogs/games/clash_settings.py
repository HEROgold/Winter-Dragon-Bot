"""Configuration settings for the Clash cog."""


class ClashSettings:
    """Settings for the Clash cog."""

    riot_api_key: Config[str | None] = Config("", optional=True)
    """Riot API key for accessing the Clash API."""
