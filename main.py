"""Main file for the bot."""

import asyncio
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from threading import Thread

import discord
from discord.ext import commands

from _types.bot import WinterDragon
from _types.errors import ConfigError
from app import app
from tools.config_reader import CONFIG_PATH, config
from tools.config_reader import get_invalid as get_invalid_configs
from tools.config_reader import is_valid as config_validator
from tools.main_log import Logs


if not config_validator():
    msg = f"""Config is not yet updated!, update the following:
        {', '.join(get_invalid_configs())}"""
    raise ConfigError(msg)


INTENTS = discord.Intents.none()
INTENTS.members = True
INTENTS.guilds = True
INTENTS.presences = True
INTENTS.guild_messages = True
INTENTS.dm_messages = True
INTENTS.moderation = True
INTENTS.message_content = True
INTENTS.auto_moderation_configuration = True
INTENTS.auto_moderation_execution = True
INTENTS.voice_states = True

bot = WinterDragon(
    intents=INTENTS,
    command_prefix=commands.when_mentioned_or(config["Main"]["prefix"]),  # type: ignore
    case_insensitive=True,
)

tree = bot.tree
threads: list[Thread] = []


def setup_logging(logger: logging.Logger, filename: str) -> None:
    logger.setLevel(config["Main"]["log_level"])
    # handler = logging.FileHandler(filename=filename, encoding="utf-8", mode="w")
    handler = RotatingFileHandler(filename=filename, backupCount=7, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(handler)


@bot.event
async def on_ready() -> None:
    invite_link = bot.get_bot_invite()

    log.bot_logger.info(f"Logged on as {bot.user}!")
    print("Bot is running!")
    print("invite link: ", invite_link)

    config.set("Main", "application_id", f"{bot.application_id}")
    config.set("Main", "bot_invite", invite_link.replace("%", "%%"))

    with open(CONFIG_PATH, "w") as f:  # noqa: ASYNC101
        config.write(f, space_around_delimiters=False)


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
        except Exception:
            log.bot_logger.exception("")


@commands.is_owner()
@tree.command(name="shutdown", description="(For bot developer only)")
async def slash_shutdown(interaction: discord.Interaction) -> None:
    try:
        await interaction.response.send_message("Shutting down.", ephemeral=True)
        log.bot_logger.info("shutdown by command.")
    except Exception:
        log.bot_logger.exception("")
    raise KeyboardInterrupt


def terminate(*args, **kwargs) -> None:
    log.bot_logger.warning(f"{args=}, {kwargs=}")
    log.bot_logger.info("terminated")
    log.shutdown()
    try:
        asyncio.ensure_future(bot.close())  # noqa: RUF006
    except Exception as e:  # noqa: BLE001
        print(e)

    for thread in threads:
        del thread
    sys.exit()


async def main() -> None:
    async with bot:
        # global here, since they should be accessible module wide,
        # but they require a running event loop
        global log  # noqa: PLW0603
        log = Logs(bot=bot)

        t = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000, "debug": False})  # noqa: S104
        t.daemon = True
        t.start()

        await mass_load()
        await bot.start(config["Tokens"]["discord_token"])


if __name__ == "__main__":
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    asyncio.run(main())
