"""Location where all endpoints to the discord API are stored."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from confkit import Config as Conf
from confkit.sentinels import UNSET
from httpxyz import URL as HTTPURL


class Config[T](Conf[T]):
    """Scoped confkit config."""

# wd-discord is a standalone library, so back its config with a package-local file
# (auto-created with the defaults below). This keeps it isolated from the app's
# config.ini. Set this file yourself *before* importing wd_discord to override.
if Config._file is UNSET:  # noqa: SLF001
    Config.set_file(Path(__file__).with_name("_discord_config.ini"))

@dataclass
class URLS:
    """Endpoints for the discord API."""

    base = Config("https://discord.com/api")
    version = Config(10)

    @property
    def api_version(self) -> str:
        """Get the API version as a string."""
        return f"v{self.version}"

class URL:
    """URL representation for the discord API."""

    def __init__(self, path: str) -> None:
        """Initialize the URL with a path."""
        self.path = path

    def __get__(self, _instance: type, _owner: type) -> HTTPURL:
        return HTTPURL(self.path)

@dataclass
class Endpoint:
    """Represents a single API endpoint."""

    url: URL
