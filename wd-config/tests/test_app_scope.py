"""Pin the app's own scopes: cog settings in cogs.ini (one section per cog)."""

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
    """Cog settings go to cogs.ini only; the app's config.ini gets no cog section."""
    boot = boot_config(COG_SETTINGS)

    assert set(boot.files) == {"cogs.ini", "config.ini"}
    assert set(boot.files["config.ini"]) == {"Settings"}


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


APP_SETTINGS = """
from wd_config import OperatorFiles
from winter_dragon.config import Settings
result = {
    "bot_name": Settings.bot_name,
    "support_guild_id": Settings.support_guild_id,
    "log_level": Settings.log_level,
    "created_color": int(Settings.created_color),
    "changed_color": int(Settings.changed_color),
    "deleted_color": int(Settings.deleted_color),
    "status_count": len(Settings.bot_status_messages),
    "unset": sorted(OperatorFiles.unset()),
}
"""


def test_fresh_boot_writes_app_settings_to_config_ini(boot_config: BootConfig) -> None:
    """With no config.ini, the app settings resolve to their defaults and are written to its Settings section."""
    boot = boot_config(APP_SETTINGS)

    assert boot.values == {
        "bot_name": "WinterDragon",
        "support_guild_id": 0,
        "log_level": 10,
        "created_color": 0x00FF00,
        "changed_color": 0xFFFF00,
        "deleted_color": 0xFF0000,
        "status_count": 12,
        "unset": [],
    }
    assert set(boot.files) == {"config.ini"}
    assert set(boot.files["config.ini"]) == {"Settings"}
    assert set(boot.files["config.ini"]["Settings"]) == {
        "bot_name",
        "support_guild_id",
        "log_level",
        "created_color",
        "changed_color",
        "deleted_color",
        "bot_status_messages",
    }


def test_prewritten_config_ini_values_resolve(boot_config: BootConfig) -> None:
    """Values already in config.ini win over the defaults."""
    boot = boot_config(
        APP_SETTINGS,
        files={"config.ini": "[Settings]\nbot_name = Smaug\nsupport_guild_id = 42\nlog_level = 20\n"},
    )

    assert boot.values["bot_name"] == "Smaug"
    assert boot.values["support_guild_id"] == 42
    assert boot.values["log_level"] == 20


def test_config_ini_is_an_operator_file(boot_config: BootConfig) -> None:
    """A `!!` value in config.ini is reported by the first-launch check."""
    boot = boot_config(APP_SETTINGS, files={"config.ini": "[Settings]\nbot_name = !!\n"})

    assert boot.values["unset"] == ["config.ini:Settings:bot_name"]


def test_cog_and_app_scopes_keep_their_own_files(boot_config: BootConfig) -> None:
    """Loading both app scopes writes each section to its own file, and neither overwrites the other."""
    boot = boot_config(COG_SETTINGS + APP_SETTINGS.replace("result = {", "result |= {"))

    assert set(boot.files["config.ini"]) == {"Settings"}
    assert set(boot.files["cogs.ini"]) == COG_SECTIONS


UNBOUND = """
from wd_config import Config
try:
    class Loose:
        value = Config(1)
    Loose.value
except Exception as e:
    result = {"raised": type(e).__name__, "message": str(e)}
else:
    result = {"raised": None}
"""


def test_descriptor_on_unbound_base_config_fails(boot_config: BootConfig) -> None:
    """The base Config has no file: a setting must belong to a bound scope, or it fails loudly."""
    boot = boot_config(UNBOUND)

    assert boot.values["raised"] is not None
    assert "Config file is not set" in boot.values["message"]
    assert boot.files == {}


CONFIRMATION_COLORS = """
import os, pathlib, re
from winter_dragon.ui import ChangedEmbed, CreatedEmbed, DeletedEmbed
before = (CreatedEmbed().color, ChangedEmbed().color, DeletedEmbed().color)
config = pathlib.Path("config.ini")
config.write_text(re.sub(r"created_color = .*", "created_color = 0x123456", config.read_text()))
stat = config.stat()
os.utime(config, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
result = {"before": before, "after": CreatedEmbed().color}
"""


def test_confirmation_embeds_read_their_color_when_created(boot_config: BootConfig) -> None:
    """Each confirmation embed takes its color from config.ini, and a color changed there shows on the next one."""
    boot = boot_config(CONFIRMATION_COLORS)

    assert boot.values == {"before": [0x00FF00, 0xFFFF00, 0xFF0000], "after": 0x123456}
