"""The app's own config scopes: app-wide settings in ``config.ini``, cog settings in ``cogs.ini``."""

import logging
from pathlib import Path

from wd_config import Config as BaseConfig
lazy from confkit.data_types import Hex, List


CONFIG_FILE = Path("config.ini")
COGS_CONFIG_FILE = Path("cogs.ini")


class Config[T](BaseConfig[T]):
    """Config descriptor scoped to the app-wide settings file."""


Config.bind(CONFIG_FILE, operator=True)


class CogConfig[T](BaseConfig[T]):
    """Config descriptor scoped to the cog settings file; every cog shares it, one section per settings class."""


CogConfig.bind(COGS_CONFIG_FILE, operator=True)


class Settings:
    """Application-wide settings."""

    bot_name = Config("WinterDragon")
    """The bot's name."""
    support_guild_id = Config(0)
    """The official support guild that /invite guild invites to; ``0`` when there is none."""
    log_level = Config(logging.DEBUG)
    """The lowest level logged, as a :mod:`logging` level number."""
    created_color = Config(Hex(0x00FF00))
    """The embed color for something created."""
    changed_color = Config(Hex(0xFFFF00))
    """The embed color for something changed."""
    deleted_color = Config(Hex(0xFF0000))
    """The embed color for something deleted."""
    bot_status_messages = Config(
        List(
            [
                "Licking a wedding cake",
                "Eating a wedding cake",
                "Comparing wedding cakes",
                "Taste testing a wedding cake",
                "Crashing a wedding to eat their cake",
                "Getting married to eat a cake",
                "Throwing a wedding cake",
                "Devouring a wedding cake",
                "Sniffing wedding cakes",
                "Touching a wedding cake",
                "Magically spawning a wedding cake",
                "Wanting to eat a wedding cake and have one too",
            ],
        ),
    )
    """The status messages the bot picks from."""
