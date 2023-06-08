import asyncio
import logging
import os
import re
import shutil
import signal
import sys
from atexit import register
from datetime import datetime

import discord
from discord.ext import commands

import config

bot_logger = logging.getLogger(f"{config.Main.BOT_NAME}")
discord_logger = logging.getLogger('discord')

bot_logger.setLevel(config.Main.LOG_LEVEL)
bot_handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
bot_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
bot_logger.addHandler(bot_handler)
bot_logger.addHandler(logging.StreamHandler())

discord_logger.setLevel(config.Main.LOG_LEVEL)
discord_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
discord_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
discord_logger.addHandler(discord_handler)    
# discord_bot_logger.addHandler(logging.StreamHandler())

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

client = discord.Client(intents=Intents)
# bot = commands.Bot(intents=Intents, command_prefix=commands.when_mentioned_or(config.Main.PREFIX), case_insensitive=True)
bot = commands.AutoShardedBot(intents=Intents, command_prefix=commands.when_mentioned_or(config.Main.PREFIX), case_insensitive=True)
tree = bot.tree


if config.Main.CUSTOM_HELP:
    bot.remove_command("help")


@bot.event
async def on_ready() -> None:
    print("Bot is running!")
    if config.Main.SHOW_LOGGED_IN == True:
        bot_logger.info(f'Logged on as {bot.user}!')


async def main() -> None:
    async with bot:
        await mass_load()
        # await bot.load_extension("jishaku")
        await bot.start(config.Tokens.DISCORD_TOKEN)


def logs_size_limit_check(size_in_kb: int) -> bool:
    total_size = sum(
        os.path.getsize(os.path.join(root, file))
        for root, _, files in os.walk(config.Main.LOG_PATH)
        for file in files
    )
    bot_logger.debug(f"{total_size=} {size_in_kb=}")
    return total_size > size_in_kb


def delete_oldest_logs() -> None:
    oldest_files = sorted(
        (
            os.path.join(root, file)
            for root, _, files in os.walk(config.Main.LOG_PATH)
            for file in files
        ),
        key=os.path.getctime,
    )
    # Some regex magic https://regex101.com/r/he2KNZ/1
    # './logs\\2023-05-08-00-10-27\\bot.log' matches into
    # /logs\\2023-05-08-00-10-27\\
    regex = r"(\./logs)(/|\d|-)+"
    folder_path = re.match(regex, oldest_files[0])[0]
    bot_logger.info(f"deleting old logs for space: {folder_path=}")
    for file in os.listdir(folder_path):
        os.remove(f"{folder_path}{file}")
    os.rmdir(folder_path)


def save_logs() -> None:
    while logs_size_limit_check(config.Main.LOG_SIZE_KB_LIMIT):
        delete_oldest_logs()
    if not os.path.exists(config.Main.LOG_PATH):
        os.mkdir(config.Main.LOG_PATH)
    log_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    if not os.path.exists(f"{config.Main.LOG_PATH}/{log_time}"):
        os.mkdir(f"{config.Main.LOG_PATH}/{log_time}")
    bot_logger.info("Saving log files")
    logging.shutdown()
    for file in os.listdir("./"):
        if file.endswith(".log"):
            print(file)
            shutil.copy(src=f"./{file}", dst=f"{config.Main.LOG_PATH}/{log_time}/{file}")


async def get_cogs() -> list[str]:
    extensions = []
    for root, _, files in os.walk("cogs"):
        extensions.extend(
            os.path.join(root, file[:-3]).replace("/", ".")
            for file in files
            if file.endswith(".py")
        )
    return extensions


async def mass_load() -> None:
    if not (os.listdir("./cogs")):
        bot_logger.critical("No Cogs Directory To Load!")
        return
    cogs = await get_cogs()
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            bot_logger.info(f"Loaded {cog}")
        except Exception as e:
            bot_logger.exception(e)


@tree.command(name = "shutdown", description = "(For bot developer only), since it runs it docker. It restarts!")
async def slash_shutdown(interaction: discord.Interaction) -> None:
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    try:
        await interaction.response.send_message("Shutting down.", ephemeral=True)
    except Exception:
        pass
    bot_logger.info("shutdown by command.")
    save_logs()
    await bot.close()
    await client.close()
    sys.exit()


@register
def terminate() -> None: 
    bot_logger.info("Logging off due to terminate")
    save_logs()
    try:
        asyncio.run(bot.close())
        asyncio.run(client.close())
    except RuntimeError:
        pass
    except Exception:
        pass
    sys.exit()


#run the bot!
if __name__ == "__main__":
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    asyncio.run(main())
