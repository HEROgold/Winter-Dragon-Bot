"""wd-bot's settings, backed by their own bot.ini file (operator and internal settings together)."""

from __future__ import annotations

lazy from pathlib import Path

lazy from confkit.data_types import List
lazy from confkit.sentinels import UNSET
lazy from wd_config import Config, OperatorFiles
lazy from wd_config.parser import REQUIRED
lazy from wd_core.constants import BOT_PERMISSIONS, intents


BOT_CONFIG_FILE = Path("bot.ini")


class BotConfig[T](Config[T]):
    """Config descriptor scoped to the bot settings file."""


BotConfig.set_file(BOT_CONFIG_FILE)
# __init_subclass__ copies the parent's parser and read-state; reset them so this
# scope detects its own parser and reads BOT_CONFIG_FILE, not CONFIG_FILE.
BotConfig._parser = UNSET  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
BotConfig._has_read_config = False  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
OperatorFiles.register(BOT_CONFIG_FILE)


class Tokens:
    """Secrets the operator fills in."""

    discord_token = BotConfig(REQUIRED)
    """The bot's token, from the Discord developer portal."""


class BotSettings:
    """How the bot connects to and presents itself on Discord."""

    application_id = BotConfig(0)
    """The bot's application ID; ``0`` looks it up from Discord on first use."""
    BOT_SCOPE = BotConfig(List(["bot"]))
    """OAuth2 scopes requested by the bot invite link."""
    intents = BotConfig(int(intents))
    """Gateway intents as an int; wrap it in ``Intents`` to use it."""
    permissions = BotConfig(int(BOT_PERMISSIONS))
    """Permissions the bot invite link asks for, as an int; wrap it in ``Permissions`` to use it."""
    auto_reload_extensions = BotConfig(default=False)
    """Reload a cog's extension module when its file changes on disk."""
    auto_reload_poll_seconds = BotConfig(5)
    """Seconds between checks of a watched extension file."""
