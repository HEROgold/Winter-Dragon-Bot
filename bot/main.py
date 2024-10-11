"""Main file for the bot."""

import asyncio
import signal
import sys

import discord
from discord.ext import commands

from bot import WinterDragon
from bot.config import config
from bot.constants import INTENTS
from bot.errors.config import ConfigError
from tools.main_log import bot_logger, logs


if not config.is_valid():
    msg = f"""Config is not yet updated!, update the following:
        {', '.join(config.get_invalid())}"""
    raise ConfigError(msg)


bot = WinterDragon(
    intents=INTENTS,
    command_prefix=commands.when_mentioned_or(config["Main"]["prefix"]),
    case_insensitive=True,
)

tree = bot.tree


@bot.event
async def on_ready() -> None:
    invite_link = bot.get_bot_invite()

    bot_logger.info(f"Logged on as {bot.user}!")
    print("Bot is running!")
    print("invite link: ", invite_link)



@commands.is_owner()
@tree.command(name="shutdown", description="(For bot developer only)")
async def slash_shutdown(interaction: discord.Interaction) -> None:
    try:
        await interaction.response.send_message("Shutting down.", ephemeral=True)
        bot_logger.info("shutdown by command.")
    except Exception:  # noqa: BLE001
        bot_logger.exception("")
    raise KeyboardInterrupt


def terminate(*args, **kwargs) -> None:
    logs.logger.warning(f"{args=}, {kwargs=}")
    logs.logger.info("terminated")
    logs.shutdown()
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.close())
    except Exception as e:  # noqa: BLE001
        print(e)
    sys.exit()


async def main() -> None:
    async with bot:
        invite_link = bot.get_bot_invite()
        config.set("Main", "application_id", f"{bot.application_id}")
        config.set("Main", "bot_invite", invite_link.replace("%", "%%"))

        bot.log_saver = asyncio.create_task(logs.daily_save_logs())
        await bot.load_extensions()
        await bot.start(config["Tokens"]["discord_token"])


if __name__ == "__main__":
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    asyncio.run(main())
