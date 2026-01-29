"""Module for a config descriptor.

The Config descriptor is used to read and write config values from a ConfigParser object.
It is used to create a descriptor for config values, preserving type information.
It also provides a way to set default values and to set config values using decorators.
"""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import TYPE_CHECKING

from confkit import Config as CKConfig


if TYPE_CHECKING:
    from collections.abc import Generator


class ConfigError(Exception):
    """Base class for all configuration-related exceptions."""


class FirstTimeLaunchError(Exception):
    """Raised when it's detected that WinterDragon is launched for the first time."""


CONFIG_FILE = Path("config.ini")


class Config[T](CKConfig[T]):
    """Config descriptor for WinterDragon."""


class ConfigParser(configparser.ConfigParser):
    """Custom config parser that handles the config file."""

    def __init__(self) -> None:
        """Initialize the config parser."""
        super().__init__()
        try:
            with CONFIG_FILE.open():
                pass
        except FileNotFoundError as e:
            CONFIG_FILE.touch(exist_ok=True)
            self._write_defaults()
            msg = f"First time launch detected, please edit settings with value !! in {CONFIG_FILE}"
            raise FirstTimeLaunchError(msg) from e
        self.read(CONFIG_FILE)

    def _write_defaults(self) -> None:
        self["Tokens"] = {
            "discord_token": "!!",
        }
        with CONFIG_FILE.open("w") as fp:
            self.write(fp)

    def is_valid(self) -> bool:
        """Check if the config is valid."""
        return all("!!" not in i for i in self.get_invalid())

    def get_invalid(self) -> Generator[str]:
        """Get all invalid config values."""
        for section in self.sections():
            for setting in self.options(section):
                if self[section][setting] == "!!":
                    yield f"{section}:{setting}"


config = ConfigParser()
Config.set_parser(config)
Config.set_file(CONFIG_FILE)
