"""Main file for the bot."""

import asyncio
import logging
import signal
import sys
from typing import Any

import discord
from config import config
from constants import INTENTS
from core.bot import WinterDragon
from discord.ext import commands
from errors.config import ConfigError


if not config.is_valid():
    msg = f"""Config is not yet updated!, update the following:
        {', '.join(config.get_invalid())}"""
    raise ConfigError(msg)

bot_logger = logging.getLogger(f"{config['Main']['bot_name']}")

bot = WinterDragon(
    intents=INTENTS,
    command_prefix=commands.when_mentioned_or(config["Main"]["prefix"]),
    case_insensitive=True,
)
tree = bot.tree


@bot.event
async def on_ready() -> None:
    """Log when the bot is ready. Note that this may happen multiple times per boot."""
    bot.get_bot_invite()

    bot_logger.info(f"Logged on as {bot.user}!")



@commands.is_owner()
@tree.command(name="shutdown", description="(For bot developer only)")
async def slash_shutdown(interaction: discord.Interaction) -> None:
    """Shutdown the bot."""
    try:
        await interaction.response.send_message("Shutting down.", ephemeral=True)
        bot_logger.info("shutdown by command.")
    except Exception:
        bot_logger.exception("")
    raise KeyboardInterrupt


def terminate(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401. Catch all arguments to log before termination.
    """Terminate the bot."""
    bot_logger.warning(f"{args=}, {kwargs=}")
    bot_logger.info("terminated")
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.close())
    except Exception:  # noqa: BLE001, S110
        pass
    sys.exit()


async def main() -> None:
    """Entrypoint of the program."""
    async with bot:
        invite_link = bot.get_bot_invite()
        config.set("Main", "application_id", f"{bot.application_id}")
        config.set("Main", "bot_invite", invite_link.replace("%", "%%"))

        await bot.load_extensions()
        await bot.start(config["Tokens"]["discord_token"])


if __name__ == "__main__":
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    asyncio.run(main())
