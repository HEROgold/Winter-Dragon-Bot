"""wd-bot's settings, backed by their own bot.ini file (operator and internal settings together)."""

lazy from pathlib import Path

lazy from confkit.data_types import List
lazy from wd_config import Config
lazy from wd_config.parser import REQUIRED
lazy from wd_core.constants import BOT_PERMISSIONS, intents


BOT_CONFIG_FILE = Path("bot.ini")


class BotConfig[T](Config[T]):
    """Config descriptor scoped to the bot settings file."""


BotConfig.bind(BOT_CONFIG_FILE, operator=True)


class Tokens:
    """Secrets the operator fills in."""

    discord_token = BotConfig(REQUIRED)
    """The bot's token, from the Discord developer portal."""
    read_only_token = BotConfig("")
    """A token for a read-only bot, if the operator wants to use one; otherwise, the bot uses its own token."""


class BotSettings:
    """How the bot connects to and presents itself on Discord."""

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
