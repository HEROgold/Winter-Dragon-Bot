"""Pin how wd-config boots today: which ini files appear, what they hold, and what settings resolve to."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


DISCORD_SETTINGS = """
from wd_config.discord import URLS, RestCache
result = {"base": URLS.base, "version": URLS.version, "ttl": RestCache.ttl}
"""


def test_empty_dir_creates_ini_files_filled_with_defaults(boot_config: BootConfig) -> None:
    """Booting with no ini files writes config.ini and discord.ini, each holding its defaults."""
    boot = boot_config(DISCORD_SETTINGS + "import wd_config.bot\n")

    assert boot.values == {"base": "https://discord.com/api", "version": 10, "ttl": 30.0}
    assert boot.files["discord.ini"]["URLS"] == {"base": "https://discord.com/api", "version": "10"}
    assert boot.files["discord.ini"]["RestCache"] == {"ttl": "30.0"}
    assert "Settings" in boot.files["config.ini"]


def test_discord_settings_stay_out_of_config_ini(boot_config: BootConfig) -> None:
    """Discord-scoped settings are written to discord.ini only."""
    boot = boot_config(DISCORD_SETTINGS)

    assert "URLS" not in boot.files.get("config.ini", {})
    assert "RestCache" not in boot.files.get("config.ini", {})


def test_prewritten_value_is_the_resolved_setting(boot_config: BootConfig) -> None:
    """A value already in the ini file wins over the default and is left on disk unchanged."""
    boot = boot_config(DISCORD_SETTINGS, files={"discord.ini": "[RestCache]\nttl = 5.5\n"})

    assert boot.values["ttl"] == 5.5
    assert boot.files["discord.ini"]["RestCache"] == {"ttl": "5.5"}


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
