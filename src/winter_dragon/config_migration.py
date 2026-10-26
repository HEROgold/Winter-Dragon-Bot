"""Where every section of the old single ``config.ini`` lives now, and the startup step that moves it there.

Only the app knows every scope, so the mapping lives here; :mod:`wd_config.migration` does the moving. The
file paths and internal defaults below can't be imported from their scopes: importing a scope reads and writes
its file, and migration has to run before that. ``wd-config/tests/test_migration.py`` pins them to the scopes.
Settings added after the split never existed in the old file, so they need no entry.
"""

import re
from pathlib import Path

lazy from wd_config.constants import DISCORD_CONFIG_FILE, SENTRY_CONFIG_FILE
lazy from wd_config.migration import MigrationReport, Move, migrate
lazy from wd_discord.log import get_logger


CONFIG_INI = Path("config.ini")
COGS_INI = Path("cogs.ini")
BOT_INI = Path("bot.ini")
DATABASE_INI = Path("database.ini")
SENTRY_INI = SENTRY_CONFIG_FILE
DISCORD_INI = DISCORD_CONFIG_FILE

_FLAG_REPR = re.compile(r"<\w+ value=(\d+)>")


def _flag_int(raw: str) -> str | None:
    """Read old intents/permissions written as an int or as ``str(Intents(...))`` (``<Intents value=N>``)."""
    raw = raw.strip()
    if raw.isdigit():
        return raw
    if match := _FLAG_REPR.fullmatch(raw):
        return match.group(1)
    return None


MOVES = (
    Move("Tokens", BOT_INI, keys={"discord_token": "discord_token"}),
    Move(
        "Settings",
        BOT_INI,
        to_section="BotSettings",
        keys={
            "bot_scope": "BOT_SCOPE",
            "auto_reload_extensions": "auto_reload_extensions",
            "auto_reload_poll_seconds": "auto_reload_poll_seconds",
        },
    ),
    Move("Settings", COGS_INI, to_section="SteamSettings", keys={"steam_redirect": "steam_redirect"}),
    Move(
        "Settings",
        CONFIG_INI,
        drop=(
            "prefix",
            "application_id",
            "bot_invite",
            "server_ip",
            "website_port",
            "website_url",
            "protocol_prefix",
            "time_format",
            "date_format",
            "datetime_format",
            "oauth_scope",
        ),
    ),
    Move(
        "BotConfig",
        BOT_INI,
        to_section="BotSettings",
        keys={"intents": "intents", "permissions": "permissions"},
        convert={"intents": _flag_int, "permissions": _flag_int},
    ),
    Move(
        "DbUrl",
        DATABASE_INI,
        keys={key: key for key in ("driver_name", "database", "username", "password", "host", "port")},
    ),
    Move("SentrySettings", SENTRY_INI, keys={"telemetry": "Telemetry", "dsn": "dsn", "environment": "environment"}),
    Move("ReminderSettings", COGS_INI),
    Move("StatsSettings", COGS_INI),
    Move("UrbanSettings", COGS_INI),
    Move("SteamSettings", COGS_INI),
    Move(
        "RateLimitHandler",
        DISCORD_INI,
        to_section="RateLimit",
        keys={"max_rate_limit_retries": "max_retries"},
        defaults={"max_retries": "5"},
    ),
    Move(
        "URLS",
        DISCORD_INI,
        keys={key: key for key in ("base", "version", "gateway", "cdn", "web", "invite")},
        defaults={
            "base": "https://discord.com/api",
            "version": "10",
            "gateway": "wss://gateway.discord.gg",
            "cdn": "https://cdn.discordapp.com",
            "web": "https://discord.com",
            "invite": "https://discord.gg",
        },
    ),
    Move("RestCache", DISCORD_INI, keys={"ttl": "ttl"}, defaults={"ttl": "30.0"}),
)
"""Every legacy section that still has a home; a section not named here is dropped."""


def migrate_legacy_config() -> MigrationReport | None:
    """Move the old single ``config.ini`` into the per-scope files, logging what moved and what was dropped.

    Run it before any settings class is imported. ``None`` when ``config.ini`` was already migrated.
    """
    logger = get_logger(__name__)
    report = migrate(CONFIG_INI, MOVES)
    if report is None:
        return None
    logger.warning(t"Migrated the old {CONFIG_INI} into per-scope files; the original is in {report.backup}")
    for moved in report.moved:
        logger.info(t"Moved {moved}")
    for kept in report.kept:
        logger.warning(t"Kept the existing {kept}; the old value is only in {report.backup}")
    for defaulted in report.defaulted:
        logger.info(t"Dropped {defaulted}: it was at its default")
    if report.dropped:
        logger.warning(t"Dropped from {CONFIG_INI} (still in {report.backup}): {', '.join(report.dropped)}")
    return report
