"""Real entrypoint for the Winter Dragon bot.

Run from the repo root with: uv run python -m winter_dragon

Constructs a wd_bot.bot.Bot and calls Bot.start() - the official (and only documented) way to
boot the bot. Bot.start() handles login, gateway connection, extension discovery/loading, and
dispatch on its own. Extensions are discovered from winter_dragon.cogs (see
Bot(extensions_package=...)), never from wd_cogs - that catalog carries discord.py-era code that
doesn't belong in src/.
"""

from __future__ import annotations

lazy import asyncio
lazy import sys

lazy from wd_bot.bot import Bot

lazy from . import cogs


async def main() -> None:
    """Construct the bot and run it forever."""
    bot = Bot(extensions_package=cogs)
    # bot.start() is decorated with @Config.with_kwarg("Tokens", "discord_token"), which
    # injects `token` into kwargs at call time - real, but not reflected in its type
    # signature, so `token` still looks required here.
    await bot.start()  # ty: ignore[invalid-await, missing-argument]


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
