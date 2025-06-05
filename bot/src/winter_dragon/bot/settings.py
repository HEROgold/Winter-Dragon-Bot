"""Module that contains Configuration."""
from __future__ import annotations

from winter_dragon.bot.config import Config


class Settings:
    """Settings for the bot."""

    log_level = Config("DEBUG", str)
    bot_name = Config("WinterDragon", str)
    support_guild_id = Config(0, int)
    prefix = Config("$", str)
    application_id = Config(None, int)
    bot_invite = Config("", str)
