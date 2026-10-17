"""Pin how wd-config boots today: which ini files appear, what they hold, and what settings resolve to."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


DISCORD_SETTINGS = """
from wd_config.discord import URLS, RateLimit, RestCache, UserAgent
result = {
    "base": URLS.base,
    "version": URLS.version,
    "ttl": RestCache.ttl,
    "max_retries": RateLimit.max_retries,
    "user_agent_url": UserAgent.url,
    "user_agent_version": UserAgent.version,
}
"""

DISCORD_DEFAULTS = {
    "base": "https://discord.com/api",
    "version": 10,
    "ttl": 30.0,
    "max_retries": 5,
    "user_agent_url": "https://github.com/HEROgold/WinterDragon",
    "user_agent_version": "0.1.0",
}


def test_empty_dir_writes_config_ini_but_not_discord_ini(boot_config: BootConfig) -> None:
    """Booting with no ini files writes config.ini; discord.ini is internal-only, so it isn't created."""
    boot = boot_config(DISCORD_SETTINGS + "import wd_config.bot\n")

    assert "Settings" in boot.files["config.ini"]
    assert "discord.ini" not in boot.files


def test_absent_discord_ini_resolves_in_code_defaults(boot_config: BootConfig) -> None:
    """Without discord.ini every discord setting resolves to its in-code default."""
    boot = boot_config(DISCORD_SETTINGS)

    assert boot.values == DISCORD_DEFAULTS
    assert "discord.ini" not in boot.files


def test_empty_discord_ini_is_filled_with_defaults(boot_config: BootConfig) -> None:
    """An existing, empty discord.ini exposes the scope: every default is written into it."""
    boot = boot_config(DISCORD_SETTINGS, files={"discord.ini": ""})

    assert boot.values == DISCORD_DEFAULTS
    assert boot.files["discord.ini"] == {
        "URLS": {"base": "https://discord.com/api", "version": "10"},
        "RestCache": {"ttl": "30.0"},
        "RateLimit": {"max_retries": "5"},
        "UserAgent": {"url": "https://github.com/HEROgold/WinterDragon", "version": "0.1.0"},
    }


def test_discord_settings_stay_out_of_config_ini(boot_config: BootConfig) -> None:
    """Discord-scoped settings are never written to config.ini."""
    boot = boot_config(DISCORD_SETTINGS + "import wd_config.bot\n", files={"discord.ini": ""})

    for section in ("URLS", "RestCache", "RateLimit", "UserAgent"):
        assert section not in boot.files["config.ini"]


def test_prewritten_value_is_the_resolved_setting(boot_config: BootConfig) -> None:
    """A value already in discord.ini wins over the default and is left on disk unchanged."""
    boot = boot_config(DISCORD_SETTINGS, files={"discord.ini": "[RestCache]\nttl = 5.5\n[RateLimit]\nmax_retries = 2\n"})

    assert boot.values["ttl"] == 5.5
    assert boot.values["max_retries"] == 2
    assert boot.files["discord.ini"]["RestCache"] == {"ttl": "5.5"}
    assert boot.files["discord.ini"]["RateLimit"] == {"max_retries": "2"}


FIRST_LAUNCH = """
from wd_config.errors import FirstTimeLaunchError
from wd_config.parser import ConfigParser
try:
    ConfigParser()
except FirstTimeLaunchError:
    result = {"raised": True}
else:
    result = {"raised": False}
parser = ConfigParser()
result |= {"valid": parser.is_valid(), "invalid": list(parser.get_invalid())}
"""


def test_first_launch_writes_token_placeholder_and_raises(boot_config: BootConfig) -> None:
    """With no config.ini, ConfigParser raises FirstTimeLaunchError and writes a `!!` discord token."""
    boot = boot_config(FIRST_LAUNCH)

    assert boot.values["raised"] is True
    assert boot.files["config.ini"] == {"Tokens": {"discord_token": "!!"}}
    assert boot.values["invalid"] == ["Tokens:discord_token"]


def test_existing_config_does_not_raise(boot_config: BootConfig) -> None:
    """An existing config.ini is read, and a filled-in token reports no invalid settings."""
    boot = boot_config(FIRST_LAUNCH, files={"config.ini": "[Tokens]\ndiscord_token = abc\n"})

    assert boot.values == {"raised": False, "valid": True, "invalid": []}
