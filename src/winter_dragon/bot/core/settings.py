"""Module that contains Configuration."""

from __future__ import annotations

import logging

from confkit import BaseDataType
from confkit.data_types import Hex, List

from .config import Config


GENERATED_MSG = "AutomaticallyGenerated"


class Combined(BaseDataType[str]):
    """A data type that combines multiple Config data types."""

    def __init__(self, *args: Config[str]) -> None:
        """Initialize with multiple Config arguments."""
        self.args = args

    def convert(self, value: str) -> str:
        """Convert from a string to the combined data type."""
        return ",".join(arg.convert(value) for arg in self.args)

    def __str__(self) -> str:
        """Return a string representation of the combined data types."""
        return ",".join(str(arg) for arg in self.args)


class Settings:
    """Application wide Settings."""

    log_level = Config(logging.DEBUG)
    bot_name = Config("WinterDragon")
    support_guild_id = Config(0)
    prefix = Config("$")
    application_id = Config(None)
    bot_invite = Config(GENERATED_MSG)

    # Colors
    created_color = Config(Hex(0x00FF00))
    changed_color = Config(Hex(0xFFFF00))
    deleted_color = Config(Hex(0xFF0000))

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

    PROTOCOL_PREFIX = Config("https://")
    SERVER_IP = Config("localhost")
    WEBSITE_PORT = Config(80)
    WEBSITE_URL = Config(Combined(PROTOCOL_PREFIX, SERVER_IP, WEBSITE_PORT))

    TIME_FORMAT = Config("%H:%M:%S")
    DATE_FORMAT = Config("%Y-%m-%d")
    DATETIME_FORMAT = Config(Combined(DATE_FORMAT, TIME_FORMAT))

    OAUTH_SCOPE = Config(
        List(
            [
                "relationships.read",
                "guilds.members.read",
                "connections",
                "email",
                "activities.read",
                "identify",
                "guilds",
                "applications.commands",
                "applications.commands.permissions.update",
            ],
        ),
    )

    BOT_SCOPE = Config(
        List(
            [
                "bot",
            ],
        ),
    )
