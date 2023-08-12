import asyncio
import logging
import os
import re
import shutil
import signal
import sys
from atexit import register
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands, tasks

from tools.config_reader import config
from tools.config_reader import is_valid as config_validator
from tools.config_reader import get_invalid as get_invalid_configs


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

bot = commands.AutoShardedBot(intents=Intents, command_prefix=commands.when_mentioned_or(config["Main"]["prefix"]), case_insensitive=True)
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
    if config["Main"]["show_logged_in"] == True:
        bot_logger.info(f"Logged on as {bot.user}!")


async def main() -> None:
    async with bot:
        await mass_load()
        # await bot.load_extension("jishaku")
        await bot.start(config["Tokens"]["discord_token"])
        daily_save_logs.start()


def logs_size_limit_check(size_in_kb: int) -> bool:
    total_size = sum(
        os.path.getsize(os.path.join(root, file))
        for root, _, files in os.walk(config["Main"]["log_path"])
        for file in files
    )
    bot_logger.debug(f"{total_size=} {size_in_kb=}")
    return total_size > size_in_kb


def delete_oldest_saved_logs() -> None:
    oldest_files = sorted((
            os.path.join(root, file)
            for root, _, files in os.walk(config["Main"]["log_path"])
            for file in files
        ),
        key=os.path.getctime,
    )
    # Some regex magic https://regex101.com/r/he2KNZ/1
    # "./logs\\2023-05-08-00-10-27\\bot.log" matches into
    # /logs\\2023-05-08-00-10-27\\
    regex = r"(\./logs)(/|\d|-|_)+"
    if os.name == "nt":
        folder_path = re.match(regex, oldest_files[0])
        # FIXME: folder_path=None
    elif os.name == "posix":
        folder_path = re.search(regex, oldest_files[0])[0]
    bot_logger.info(f"deleting old logs for space: {folder_path=}")
    
    for file in os.listdir(folder_path):
        os.remove(f"{folder_path}{file}")
    os.rmdir(folder_path)


def save_logs() -> None:
    # FIXME: fix issue where logs stay on top level
    while logs_size_limit_check(int(config["Main"]["log_size_kb_limit"])):
        delete_oldest_saved_logs()

    if not os.path.exists(config["Main"]["log_path"]):
        os.mkdir(config["Main"]["log_path"])

    log_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    if not os.path.exists(f"{config['Main']['log_path']}/{log_time}"):
        os.mkdir(f"{config['Main']['log_path']}/{log_time}")

    bot_logger.info("Saving log files")
    bot_logger.info(f"Bot uptime: {datetime.now(timezone.utc) - bot.launch_time}")

    for file in os.listdir("./"):
        if file.endswith(".log") or file[:-2].endswith(".log"):
            print(file)
            shutil.copy(src=f"./{file}", dst=f"{config['Main']['log_path']}/{log_time}/{file}")
    logging_rollover()


def logging_rollover() -> None:
    from tools.database_tables import logger as sql_logger
    log_handlers = []
    log_handlers.extend(sql_logger.handlers)
    log_handlers.extend(discord_logger.handlers)
    log_handlers.extend(bot_logger.handlers)
    for handler in log_handlers:
        if isinstance(handler, RotatingFileHandler):
            handler.doRollover()


def delete_toplevel_logs() -> None:
    if config["Main"]["keep_latest_logs"]:
        return
    for file in os.listdir("./"):
        if file.endswith(".log") or file[:-2].endswith(".log"):
            print(f"Removing {file}")
            os.remove(file)


@tasks.loop(hours=24)
async def daily_save_logs() -> None:
    save_logs()


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
        bot_logger.critical("No extensions Directory To Load!")
        return
    for extension in await get_extensions():
        try:
            await bot.load_extension(extension)
            bot_logger.info(f"Loaded {extension}")
        except Exception as e:
            bot_logger.exception(e)


@tree.command(name = "shutdown", description = "(For bot developer only)")
@commands.is_owner()
async def slash_shutdown(interaction: discord.Interaction) -> None:
    try:
        await interaction.response.send_message("Shutting down.", ephemeral=True)
        bot_logger.info("shutdown by command.")
        save_logs()
        await bot.close()
        delete_toplevel_logs()
    except Exception: pass
    sys.exit()


@register
def terminate() -> None: 
    bot_logger.info("Logging off due to terminate")
    save_logs()
    try:
        asyncio.run(bot.close())
        delete_toplevel_logs()
    except Exception: pass
    sys.exit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)

    delete_toplevel_logs()

    bot_logger = logging.getLogger(f"{config['Main']['bot_name']}")
    discord_logger = logging.getLogger("discord")
    setup_logging(bot_logger, "bot.log")
    setup_logging(discord_logger, "discord.log")
    bot_logger.addHandler(logging.StreamHandler())

    asyncio.run(main())

