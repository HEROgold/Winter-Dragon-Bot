"""Run a real wd_bot.Bot for up to 10 minutes against the live Discord API.

Run from the repo root: uv run python -m winter_dragon.run_test_bot

Demonstrates the intended end-user experience: construct Bot and call .start() - it handles
login, gateway connection, extension discovery/loading, and dispatch on its own, unlike the
low-level tests/verify_*.py drivers that drive wd_discord.Client/Gateway directly. Extensions
are discovered from winter_dragon.cogs (see Bot(extensions_package=...)), never from wd_cogs -
that catalog carries discord.py-era code that doesn't belong in src/.

Uses a local sqlite engine instead of the configured Postgres backend - Cog.__init__ needs some
engine either way, and wd_db.constants eagerly creates a real Postgres engine at import time
that needs psycopg2 (not installed in this dev environment). This is how a lightweight/dev bot
would actually be configured, not a hack specific to this being a test - see
wd-bot/tests/test_bot.py's identical stub for the same reason. The stub is installed in
sys.modules before anything else runs, so the real wd_db.constants module body never executes.

Enables Sentry with environment=test (restored to its original value on exit either way) and
points herogold's logger at ./logs so a DEBUG-level .log file is left behind for inspection -
herogold hardcodes DEBUG for both the global and per-class loggers already; set_log_directory
just makes sure the resulting files land somewhere predictable.
"""

from __future__ import annotations

lazy import asyncio
lazy import sys
lazy import types

lazy from herogold.log import LoggerMixin
lazy from sqlmodel import create_engine
lazy from wd_bot.bot import Bot
lazy from wd_config.sentry import Environments, SentrySettings
lazy from wd_core.intents import Intents
lazy from wd_discord import Sentry

lazy from . import cogs  # noqa: F401 - imported for its side effect: registers winter_dragon.cogs as a real package


RUN_DURATION_SECONDS = 600


def _stub_wd_db_engine() -> None:
    """Install a sqlite-backed wd_db.constants stub before anything imports the real one."""
    stub = types.ModuleType("wd_db.constants")
    stub.engine = create_engine("sqlite://")
    sys.modules["wd_db.constants"] = stub


async def main() -> int:
    """Run the bot for up to RUN_DURATION_SECONDS, then report the outcome."""
    _stub_wd_db_engine()

    LoggerMixin.set_log_directory("logs")

    original_environment = SentrySettings.environment
    SentrySettings.environment = Environments.test  # ty: ignore[invalid-assignment] - Config descriptor set-type
    try:
        Sentry()

        # message_content/guild_messages are needed for MessageLogger to see anything -
        # the config.ini default (BotConfig.Intents = 0) would leave the bot deaf to both.
        intents = Intents.guilds | Intents.guild_messages | Intents.message_content
        bot = Bot(intents=intents, extensions_package="winter_dragon.cogs")
        try:
            # bot.start() is decorated with @Config.with_kwarg("Tokens", "discord_token"), which
            # injects `token` into kwargs at call time - real, but not reflected in its type
            # signature, so `token` still looks required here.
            await asyncio.wait_for(bot.start(), timeout=RUN_DURATION_SECONDS)  # ty: ignore[invalid-argument-type, missing-argument]
        except TimeoutError:
            pass
        else:
            return 1
    finally:
        SentrySettings.environment = original_environment  # ty: ignore[invalid-assignment]

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
