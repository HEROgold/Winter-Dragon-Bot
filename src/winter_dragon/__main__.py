"""Real entrypoint for the Winter Dragon bot.

Run from the repo root with: uv run python -m winter_dragon

Constructs a wd_bot.bot.Bot and calls Bot.start() - the official (and only documented) way to
boot the bot. Bot.start() handles login, gateway connection, extension discovery/loading, and
dispatch on its own. Extensions are discovered from winter_dragon.cogs (see
Bot(extensions_package=...)), never from wd_cogs - that catalog carries discord.py-era code that
doesn't belong in src/.
"""

lazy import asyncio
lazy import importlib
lazy import sys

from wd_core.sentry import Sentry
lazy from wd_bot.bot import Bot

lazy from . import cogs
lazy from .config_migration import migrate_legacy_config


async def main() -> None:
    """Migrate an old config.ini, then construct the bot and run it forever."""
    # Before any settings class is imported: confkit reads each ini file once, when its class is defined.
    migrate_legacy_config()
    # Defining the app's scopes registers config.ini and cogs.ini with OperatorFiles, which bot.start() checks.
    importlib.import_module(f"{__package__}.config")
    bot = Bot(extensions_package=cogs)
    # bot.start() is decorated with @BotConfig.with_kwarg("Tokens", "discord_token"), reading bot.ini, which
    # injects `token` into kwargs at call time - real, but not reflected in its type
    # signature, so `token` still looks required here.
    Sentry()
    await bot.start()  # ty: ignore[invalid-await, missing-argument]


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
