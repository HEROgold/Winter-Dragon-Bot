"""Pin wd-bot's bot.ini scope: what a boot writes there, what resolves from it, and the first-launch check."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


BOT_SETTINGS = """
from wd_bot.settings import BotSettings, Tokens
result = {
    "token": Tokens.discord_token,
    "scope": list(BotSettings.BOT_SCOPE),
    "auto_reload": BotSettings.auto_reload_extensions,
    "poll": BotSettings.auto_reload_poll_seconds,
    "intents": BotSettings.intents,
    "permissions": BotSettings.permissions,
}
"""

DEFAULTS = """
from wd_core.constants import BOT_PERMISSIONS, intents
result |= {"default_intents": int(intents), "default_permissions": int(BOT_PERMISSIONS)}
"""


def test_fresh_boot_writes_bot_ini_defaults(boot_config: BootConfig) -> None:
    """With no bot.ini, the bot settings resolve to their defaults and are written to bot.ini."""
    boot = boot_config(BOT_SETTINGS + DEFAULTS)
    values = boot.values

    assert values["token"] == "!!"
    assert values["scope"] == ["bot"]
    assert values["auto_reload"] is False
    assert values["poll"] == 5
    assert values["intents"] == values["default_intents"]
    assert values["permissions"] == values["default_permissions"]
    assert boot.files["bot.ini"]["Tokens"] == {"discord_token": "!!"}
    assert boot.files["bot.ini"]["BotSettings"]["intents"] == str(values["default_intents"])


def test_prewritten_bot_ini_values_resolve(boot_config: BootConfig) -> None:
    """Values already in bot.ini win over the defaults."""
    boot = boot_config(
        BOT_SETTINGS,
        files={
            "bot.ini": (
                "[Tokens]\ndiscord_token = abc\n"
                "[BotSettings]\nBOT_SCOPE = bot,applications.commands\n"
                "auto_reload_extensions = True\nauto_reload_poll_seconds = 2\nintents = 3\npermissions = 8\n"
            ),
        },
    )

    assert boot.values == {
        "token": "abc",
        "scope": ["bot", "applications.commands"],
        "auto_reload": True,
        "poll": 2,
        "intents": 3,
        "permissions": 8,
    }


def test_bot_settings_stay_out_of_config_ini(boot_config: BootConfig) -> None:
    """No bot setting lands in config.ini next to the remaining application-wide settings."""
    boot = boot_config(BOT_SETTINGS + "import winter_dragon.config\n")
    config = boot.files["config.ini"]

    assert "Tokens" not in config
    assert "BotSettings" not in config
    assert {"BOT_SCOPE", "auto_reload_extensions", "auto_reload_poll_seconds"}.isdisjoint(
        config["Settings"],
    )


START = """
import asyncio
from wd_config.errors import FirstTimeLaunchError
from wd_bot.bot import Bot
try:
    asyncio.run(Bot().start())
except FirstTimeLaunchError as e:
    result = {"raised": "FirstTimeLaunchError", "message": str(e)}
except BaseException as e:
    result = {"raised": type(e).__name__, "message": str(e)}
"""


def test_start_stops_on_unset_token_before_connecting(boot_config: BootConfig) -> None:
    """`Bot.start` with the `!!` token raises FirstTimeLaunchError naming bot.ini, without contacting Discord."""
    boot = boot_config(START)

    assert boot.values["raised"] == "FirstTimeLaunchError"
    assert "bot.ini:Tokens:discord_token" in boot.values["message"]
