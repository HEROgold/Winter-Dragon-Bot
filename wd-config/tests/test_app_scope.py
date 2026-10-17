"""Pin the app's own scopes: cog settings in cogs.ini (one section per cog)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


COG_SETTINGS = """
from wd_config import OperatorFiles
from winter_dragon.cogs.reminder import ReminderSettings
from winter_dragon.cogs.stats import StatsSettings
from winter_dragon.cogs.steam.settings import SteamSettings
from winter_dragon.cogs.urban import UrbanSettings
result = {
    "check_interval": ReminderSettings.check_interval,
    "stats_interval": StatsSettings.update_interval,
    "country_code": SteamSettings.country_code,
    "request_interval": SteamSettings.request_interval,
    "steam_redirect": SteamSettings.steam_redirect,
    "allow_random": UrbanSettings.allow_random,
    "max_definitions": UrbanSettings.max_definitions,
    "unset": sorted(key for key in OperatorFiles.unset() if key.startswith("cogs.ini")),
}
"""

COG_SECTIONS = {"ReminderSettings", "StatsSettings", "SteamSettings", "UrbanSettings"}


def test_fresh_boot_writes_cog_settings_to_cogs_ini(boot_config: BootConfig) -> None:
    """With no cogs.ini, every cog's settings resolve to their defaults and are written there, one section each."""
    boot = boot_config(COG_SETTINGS)

    assert boot.values == {
        "check_interval": 60,
        "stats_interval": 3600,
        "country_code": "US",
        "request_interval": 1.5,
        "steam_redirect": "steam://",
        "allow_random": True,
        "max_definitions": 5,
        "unset": [],
    }
    assert set(boot.files["cogs.ini"]) == COG_SECTIONS
    assert boot.files["cogs.ini"]["SteamSettings"]["steam_redirect"] == "steam://"


def test_cog_settings_create_no_other_file(boot_config: BootConfig) -> None:
    """Reading cog settings writes cogs.ini, and database.ini for the cogs' tables, so none lands in config.ini."""
    boot = boot_config(COG_SETTINGS)

    assert set(boot.files) == {"cogs.ini", "database.ini"}
    assert COG_SECTIONS.isdisjoint(boot.files["database.ini"])


def test_prewritten_cogs_ini_values_resolve(boot_config: BootConfig) -> None:
    """Values already in cogs.ini win over the defaults."""
    boot = boot_config(
        COG_SETTINGS,
        files={
            "cogs.ini": (
                "[ReminderSettings]\ncheck_interval = 5\n"
                "[StatsSettings]\nupdate_interval = 600\n"
                "[SteamSettings]\ncountry_code = NL\nrequest_interval = 3.0\nsteam_redirect = https://x.example/\n"
                "[UrbanSettings]\nallow_random = False\nmax_definitions = 2\n"
            ),
        },
    )

    assert boot.values == {
        "check_interval": 5,
        "stats_interval": 600,
        "country_code": "NL",
        "request_interval": 3.0,
        "steam_redirect": "https://x.example/",
        "allow_random": False,
        "max_definitions": 2,
        "unset": [],
    }


def test_cogs_ini_is_an_operator_file(boot_config: BootConfig) -> None:
    """A `!!` value in cogs.ini is reported by the first-launch check."""
    boot = boot_config(COG_SETTINGS, files={"cogs.ini": "[UrbanSettings]\nmax_definitions = 5\napi_key = !!\n"})

    assert boot.values["unset"] == ["cogs.ini:UrbanSettings:api_key"]
