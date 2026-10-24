"""Pin the one-off migration of the old single config.ini into the per-scope ini files."""

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


LEGACY_CONFIG = """
[Tokens]
discord_token = fake-token-123

[Settings]
prefix = $
bot_name = Smaug
support_guild_id = 42
log_level = 20
created_color = 0x112233
changed_color = 0x445566
deleted_color = 0x778899
bot_status_messages = Hoarding gold,Sleeping on gold
application_id = 1234567890
bot_scope = bot,applications.commands
auto_reload_extensions = True
auto_reload_poll_seconds = 2
steam_redirect = https://redirect.example/
bot_invite = https://invite.example/
server_ip = 127.0.0.1
website_port = 5000
website_url = https://site.example/
protocol_prefix = https://
time_format = %%H:%%M
date_format = %%d-%%m-%%Y
datetime_format = %%d-%%m-%%Y %%H:%%M
oauth_scope = identify

[BotConfig]
intents = <Intents value=3276799>
permissions = 70368744177655

[DbUrl]
drivername = sqlite
driver_name = postgresql
database = dragon
username = smaug
password = fake-db-password
host = db.example
port = 5433

[SentrySettings]
telemetry = False
dsn = https://fake@sentry.example/1
environment = production

[ReminderSettings]
check_interval = 30

[StatsSettings]
update_interval = 1800

[UrbanSettings]
allow_random = False
max_definitions = 3

[SteamSettings]
country_code = NL
request_interval = 2.5

[RateLimitHandler]
max_rate_limit_retries = 5

[Redis]
host = redis

[WorkerScaling]
max_workers = 4

[LogsManager]
log_channel = 99
"""

MIGRATE = """
from pathlib import Path
from winter_dragon.config_migration import migrate_legacy_config
report = migrate_legacy_config()
backups = sorted(path.name for path in Path().glob("config.ini.bak*"))
result = {
    "migrated": report is not None,
    "dropped": sorted(report.dropped) if report else [],
    "kept": sorted(report.kept) if report else [],
    "backups": backups,
    "backup_text": [Path(name).read_text(encoding="utf-8") for name in backups],
}
"""


def test_legacy_sections_move_to_their_new_files(boot_config: BootConfig) -> None:
    """Every known legacy section and key lands in its new file and section with its value preserved."""
    boot = boot_config(MIGRATE, files={"config.ini": LEGACY_CONFIG})

    assert boot.values["migrated"] is True
    assert boot.files["config.ini"] == {
        "Settings": {
            "bot_name": "Smaug",
            "support_guild_id": "42",
            "log_level": "20",
            "created_color": "0x112233",
            "changed_color": "0x445566",
            "deleted_color": "0x778899",
            "bot_status_messages": "Hoarding gold,Sleeping on gold",
        },
    }
    assert boot.files["bot.ini"] == {
        "Tokens": {"discord_token": "fake-token-123"},
        "BotSettings": {
            "BOT_SCOPE": "bot,applications.commands",
            "auto_reload_extensions": "True",
            "auto_reload_poll_seconds": "2",
            "intents": "3276799",
            "permissions": "70368744177655",
        },
    }
    assert boot.files["database.ini"] == {
        "DbUrl": {
            "driver_name": "postgresql",
            "database": "dragon",
            "username": "smaug",
            "password": "fake-db-password",
            "host": "db.example",
            "port": "5433",
        },
    }
    assert boot.files["sentry.ini"] == {
        "SentrySettings": {"Telemetry": "False", "dsn": "https://fake@sentry.example/1", "environment": "production"},
    }
    assert boot.files["cogs.ini"] == {
        "ReminderSettings": {"check_interval": "30"},
        "StatsSettings": {"update_interval": "1800"},
        "UrbanSettings": {"allow_random": "False", "max_definitions": "3"},
        "SteamSettings": {
            "country_code": "NL",
            "request_interval": "2.5",
            "steam_redirect": "https://redirect.example/",
        },
    }


def test_original_is_backed_up(boot_config: BootConfig) -> None:
    """The untouched legacy file is copied to config.ini.bak before anything is rewritten."""
    boot = boot_config(MIGRATE, files={"config.ini": LEGACY_CONFIG})

    assert boot.values["backups"] == ["config.ini.bak"]
    assert boot.values["backup_text"] == [LEGACY_CONFIG]


def test_existing_backup_is_never_overwritten(boot_config: BootConfig) -> None:
    """An older config.ini.bak stays; the new backup takes the next free numbered name."""
    boot = boot_config(MIGRATE, files={"config.ini": LEGACY_CONFIG, "config.ini.bak": "[Old]\nkey = 1\n"})

    assert boot.values["backups"] == ["config.ini.bak", "config.ini.bak.1"]
    assert boot.values["backup_text"] == ["[Old]\nkey = 1\n", LEGACY_CONFIG]


def test_dead_sections_and_keys_are_dropped_and_reported(boot_config: BootConfig) -> None:
    """Sections and keys nothing declares are dropped (they stay in the backup) and reported by name."""
    boot = boot_config(MIGRATE, files={"config.ini": LEGACY_CONFIG})

    assert boot.values["dropped"] == sorted(
        [
            "DbUrl.drivername",
            "LogsManager",
            "Redis",
            "Settings.application_id",
            "Settings.bot_invite",
            "Settings.date_format",
            "Settings.datetime_format",
            "Settings.oauth_scope",
            "Settings.prefix",
            "Settings.protocol_prefix",
            "Settings.server_ip",
            "Settings.time_format",
            "Settings.website_port",
            "Settings.website_url",
            "WorkerScaling",
        ],
    )


def test_internal_value_at_default_creates_no_internal_file(boot_config: BootConfig) -> None:
    """A legacy internal value still at its in-code default is dropped, so discord.ini isn't created."""
    boot = boot_config(MIGRATE, files={"config.ini": LEGACY_CONFIG})

    assert "discord.ini" not in boot.files


def test_changed_internal_value_creates_the_internal_file(boot_config: BootConfig) -> None:
    """A legacy internal value changed from its default is kept, creating discord.ini with only that value."""
    legacy = LEGACY_CONFIG.replace("max_rate_limit_retries = 5", "max_rate_limit_retries = 9")
    legacy += "\n[URLS]\nversion = 10\ncdn = https://cdn.example\n"
    boot = boot_config(MIGRATE, files={"config.ini": legacy})

    assert boot.files["discord.ini"] == {"RateLimit": {"max_retries": "9"}, "URLS": {"cdn": "https://cdn.example"}}


def test_required_placeholder_is_filled_but_real_values_are_kept(boot_config: BootConfig) -> None:
    """An existing target still at `!!` takes the legacy value; a real value in it isn't overwritten."""
    boot = boot_config(
        MIGRATE,
        files={
            "config.ini": LEGACY_CONFIG,
            "bot.ini": "[Tokens]\ndiscord_token = !!\n\n[BotSettings]\nauto_reload_poll_seconds = 7\n",
        },
    )

    assert boot.files["bot.ini"]["Tokens"] == {"discord_token": "fake-token-123"}
    assert boot.files["bot.ini"]["BotSettings"]["auto_reload_poll_seconds"] == "7"
    assert boot.values["kept"] == ["bot.ini:BotSettings.auto_reload_poll_seconds"]


def test_unparseable_intents_are_dropped(boot_config: BootConfig) -> None:
    """Old intents that aren't an int or an `<Intents value=N>` repr are dropped and reported."""
    legacy = LEGACY_CONFIG.replace("intents = <Intents value=3276799>", "intents = everything")
    boot = boot_config(MIGRATE, files={"config.ini": legacy})

    assert "intents" not in boot.files["bot.ini"]["BotSettings"]
    assert "BotConfig.intents" in boot.values["dropped"]


def test_second_run_changes_nothing(boot_config: BootConfig) -> None:
    """Once migrated, a later start finds nothing to move and leaves every file alone."""
    first = boot_config(MIGRATE, files={"config.ini": LEGACY_CONFIG})
    second = boot_config(MIGRATE)

    assert second.values["migrated"] is False
    assert second.values["backups"] == ["config.ini.bak"]
    assert second.files == first.files


def test_current_config_ini_is_left_alone(boot_config: BootConfig) -> None:
    """A config.ini holding only the app's settings, even ones the mapping doesn't list, isn't migrated."""
    boot = boot_config(MIGRATE, files={"config.ini": "[Settings]\nbot_name = Smaug\nnew_setting = 1\n"})

    assert boot.values["migrated"] is False
    assert boot.values["backups"] == []
    assert boot.files["config.ini"] == {"Settings": {"bot_name": "Smaug", "new_setting": "1"}}


def test_missing_config_ini_is_not_migrated(boot_config: BootConfig) -> None:
    """Without a config.ini there is nothing to migrate and no file is written."""
    boot = boot_config(MIGRATE)

    assert boot.values["migrated"] is False
    assert boot.files == {}


def test_migrated_files_resolve_through_their_scopes(boot_config: BootConfig) -> None:
    """After migration the real settings classes read the moved values."""
    boot = boot_config(
        MIGRATE
        + """
from wd_bot.settings import BotSettings, Tokens
from wd_db.settings import DbUrl
from wd_config.sentry import SentrySettings
from winter_dragon.cogs.steam.settings import SteamSettings
from winter_dragon.config import Settings
result |= {
    "token": Tokens.discord_token,
    "intents": BotSettings.intents,
    "scope": list(BotSettings.BOT_SCOPE),
    "port": DbUrl.port,
    "telemetry": SentrySettings.Telemetry,
    "redirect": SteamSettings.steam_redirect,
    "bot_name": Settings.bot_name,
}
""",
        files={"config.ini": LEGACY_CONFIG},
    )

    assert {key: boot.values[key] for key in ("token", "intents", "scope", "port", "telemetry", "redirect", "bot_name")} == {
        "token": "fake-token-123",
        "intents": 3276799,
        "scope": ["bot", "applications.commands"],
        "port": 5433,
        "telemetry": False,
        "redirect": "https://redirect.example/",
        "bot_name": "Smaug",
    }


def test_mapping_matches_the_scopes(boot_config: BootConfig) -> None:
    """The migration's target files and internal defaults are the ones the scopes bind and write."""
    boot = boot_config(
        """
from wd_bot.settings import BOT_CONFIG_FILE
from wd_config.constants import DISCORD_CONFIG_FILE, SENTRY_CONFIG_FILE
from wd_db.settings import DATABASE_CONFIG_FILE
from winter_dragon import config_migration as migration
from winter_dragon.config import COGS_CONFIG_FILE, CONFIG_FILE
import wd_config.discord
result = {
    "files": [
        str(migration.CONFIG_INI) == str(CONFIG_FILE),
        str(migration.COGS_INI) == str(COGS_CONFIG_FILE),
        str(migration.BOT_INI) == str(BOT_CONFIG_FILE),
        str(migration.DATABASE_INI) == str(DATABASE_CONFIG_FILE),
        str(migration.SENTRY_INI) == str(SENTRY_CONFIG_FILE),
        str(migration.DISCORD_INI) == str(DISCORD_CONFIG_FILE),
    ],
    "defaults": {
        f"{move.to_section or move.section}.{key}": value
        for move in migration.MOVES
        for key, value in (move.defaults or {}).items()
    },
}
""",
        files={"discord.ini": ""},
    )

    assert all(boot.values["files"])
    written = boot.files["discord.ini"]
    for name, default in boot.values["defaults"].items():
        section, key = name.split(".")
        assert written[section][key] == default, name
