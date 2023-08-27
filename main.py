import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands

from tools.config_reader import config
from tools.config_reader import is_valid as config_validator
from tools.config_reader import get_invalid as get_invalid_configs
from tools.main_log import Logs
from _types.bot import WinterDragon

if not config_validator():
    raise ValueError(f"Config is not yet updated!, update the following:\n{', '.join(get_invalid_configs())}")


Intents = discord.Intents.none()
Intents.members = True
Intents.guilds = True
Intents.presences = True
Intents.guild_messages = True
Intents.dm_messages = True
Intents.moderation = True
Intents.message_content = True
Intents.auto_moderation_configuration = True
Intents.auto_moderation_execution = True

bot = WinterDragon(intents=Intents, command_prefix=commands.when_mentioned_or(config["Main"]["prefix"]), case_insensitive=True)
bot.launch_time = datetime.now(timezone.utc)
tree = bot.tree


def setup_logging(logger: logging.Logger, filename: str) -> None:
    logger.setLevel(config["Main"]["log_level"])
    # handler = logging.FileHandler(filename=filename, encoding="utf-8", mode="w")
    handler = RotatingFileHandler(filename=filename, backupCount=7, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(handler)


if config["Main"]["custom_help"]:
    bot.remove_command("help")


@bot.event
async def on_ready() -> None:
    print("Bot is running!")
    if config.getboolean("Main", "show_logged_in"):
        log.bot_logger.info(f"Logged on as {bot.user}!")


async def get_extensions() -> list[str]:
    extensions = []
    for root, _, files in os.walk("extensions"):
        extensions.extend(
            os.path.join(root, file[:-3]).replace("/", ".").replace("\\", ".")
            for file in files
            if file.endswith(".py")
        )
    return extensions


async def mass_load() -> None:
    if not (os.listdir("./extensions")):
        log.bot_logger.critical("No extensions Directory To Load!")
        return
    for extension in await get_extensions():
        try:
            await bot.load_extension(extension)
            log.bot_logger.info(f"Loaded {extension}")
        except Exception as e:
            log.bot_logger.exception(e)


@commands.is_owner()
@tree.command(name = "shutdown", description = "(For bot developer only)")
async def slash_shutdown(interaction: discord.Interaction) -> None:
    try:
        await interaction.response.send_message("Shutting down.", ephemeral=True)
        log.bot_logger.info("shutdown by command.")
    except Exception: pass
    raise KeyboardInterrupt


def terminate(*args, **kwargs) -> None: 
    log.bot_logger.warning(f"{args=}, {kwargs=}")
    log.bot_logger.info("terminated")
    log.shutdown()
    try:
        asyncio.ensure_future(bot.close())
        # asyncio.run(bot.close())
    except Exception: pass
    sys.exit()


async def main() -> None:
    async with bot:
        # global here, since they should be accessible module wide,
        # but they require a running even loop
        global log
        log = Logs(bot=bot)

        await mass_load()
        # await bot.load_extension("jishaku")
        await bot.start(config["Tokens"]["discord_token"])
        log.daily_save_logs.start()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    asyncio.run(main())
