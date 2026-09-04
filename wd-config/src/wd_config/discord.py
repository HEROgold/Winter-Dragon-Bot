"""Discord-scoped configuration, backed by its own discord.ini file."""

from __future__ import annotations

lazy from dataclasses import dataclass

lazy from confkit.sentinels import UNSET

lazy from .config import Config
lazy from .constants import DISCORD_CONFIG_FILE


class DiscordConfig[T](Config[T]):
    """Config descriptor scoped to the discord settings file."""


DiscordConfig.set_file(DISCORD_CONFIG_FILE)
# __init_subclass__ copies the parent's parser and read-state; reset them so this
# scope detects its own parser and reads DISCORD_CONFIG_FILE, not CONFIG_FILE.
DiscordConfig._parser = UNSET  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
DiscordConfig._has_read_config = False  # pyright: ignore[reportPrivateUsage] # noqa: SLF001


@dataclass
class URLS:
    """Endpoints for the discord API."""

    base = DiscordConfig("https://discord.com/api")
    version = DiscordConfig(10)

    @property
    def api_version(self) -> str:
        """Get the API version as a string."""
        return f"v{self.version}"
