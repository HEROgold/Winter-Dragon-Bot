"""Module for a config descriptor.

The Config descriptor is used to read and write config values from a ConfigParser object.
It is used to create a descriptor for config values, preserving type information.
It also provides a way to set default values and to set config values using decorators.
"""

from __future__ import annotations

import configparser
from typing import TYPE_CHECKING

from confkit import Config

from winter_dragon.bot.core.paths import BOT_CONFIG
from winter_dragon.bot.errors.config import FirstTimeLaunchError


if TYPE_CHECKING:
    from collections.abc import Generator

# TODO: remove dependency on winter_dragon.bot files.
class ConfigParser(configparser.ConfigParser):
    """Custom config parser that handles the config file."""

    def __init__(self) -> None:
        """Initialize the config parser."""
        super().__init__()
        try:
            with BOT_CONFIG.open():
                pass
        except FileNotFoundError as e:
            BOT_CONFIG.touch(exist_ok=True)
            self._write_defaults()
            msg = f"First time launch detected, please edit settings with value !! in {BOT_CONFIG}"
            raise FirstTimeLaunchError(msg) from e
        self.read(BOT_CONFIG)

    def _write_defaults(self) -> None:
        self["Tokens"] = {
            "discord_token": "!!",
        }
        with BOT_CONFIG.open("w") as fp:
            self.write(fp)

    def is_valid(self) -> bool:
        """Check if the config is valid."""
        for section in self.sections():
            for setting in self.options(section):
                if self[section][setting] == "!!":
                    return False
        return True

    def get_invalid(self) -> Generator[str]:
        """Get all invalid config values."""
        for section in self.sections():
            for setting in self.options(section):
                if self[section][setting] == "!!":
                    yield f"{section}:{setting}"

config = ConfigParser()
Config.set_parser(config)
Config.set_file(BOT_CONFIG)

