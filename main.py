import asyncio
import logging
import os
import shutil
import sys
from atexit import register
from datetime import datetime

import discord
from discord.ext import commands

import config

# Change values/settings in config.py.
# TODO: Push owner only commands in specific guild.
# TODO: write dpy/pytests

LOG_LEVEL = logging.DEBUG

bot_logger = logging.getLogger(f"{config.Main.BOT_NAME}")
discord_logger = logging.getLogger('discord')

bot_logger.setLevel(LOG_LEVEL)
bot_handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
bot_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
bot_logger.addHandler(bot_handler)
bot_logger.addHandler(logging.StreamHandler())

discord_logger.setLevel(logging.INFO)
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
bot = commands.Bot(intents=Intents, command_prefix=commands.when_mentioned_or(config.Main.PREFIX), case_insensitive=True)
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
        await bot.load_extension("jishaku")
        await bot.start(config.Tokens.DICSORD_TOKEN)


def logs_size_limit_check(size_in_kb: int) -> bool:
    total_size = sum(
        os.path.getsize(os.path.join(root, file))
        for root, _, files in os.walk(config.Main.LOG_PATH)
        for file in files
    )
    bot_logger.debug(f"{total_size=} {size_in_kb=}")
    return total_size > size_in_kb
    # if returns true, def function to remove the oldest logs

def delete_oldest_logs() -> None:
    # TODO: 
    # refactor code, store sizes in dict, then remove oldest X needed
    # to stay under set limit.
    oldest_files = sorted(
        (
            os.path.join(root, file)
            for root, _, files in os.walk(config.Main.LOG_PATH)
            for file in files
        ),
        key=os.path.getctime,
    )
    bot_logger.info(f"deleting old log for space: {oldest_files}")
    os.remove(oldest_files[0])
    # TODO: remove empty directories
    # https://stackoverflow.com/questions/10989005/do-i-understand-os-walk-right
    # for root, dirs, files in os.walk(config.Main.LOG_PATH):
    #     for dir in dirs:
    #         for file in files:
    #             os.path.join(root, dirs, file)

def save_logs() -> None:
    while logs_size_limit_check(config.Main.LOG_SIZE_KB_LIMIT):
        delete_oldest_logs()
    if not os.path.exists(config.Main.LOG_PATH):
        os.mkdir(config.Main.LOG_PATH)
    log_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    if not os.path.exists(f"{config.Main.LOG_PATH}/{log_time}"):
        os.mkdir(f"{config.Main.LOG_PATH}/{log_time}")
    bot_logger.info("Saved log files")
    shutil.copy(src="bot.log", dst=f"{config.Main.LOG_PATH}/{log_time}/bot.log")
    shutil.copy(src="discord.log", dst=f"{config.Main.LOG_PATH}/{log_time}/discord.log")

async def get_cogs() -> list[str]:
    extensions = []
    for root, _, files in os.walk("cogs"):
        extensions.extend(
            os.path.join(root, file[:-3]).replace("\\", ".")
            for file in files
            if file.endswith(".py")
        )
    return extensions

async def mass_load() -> None:
    cogs = await get_cogs()
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            bot_logger.info(f"Loaded {cog}")
        except Exception as e:
            bot_logger.exception(e)
    if not (os.listdir("./cogs")):
        bot_logger.warning("No Cogs Directory To Load!")

@tree.command(
    name = "shutdown",
    description = "(For bot developer only)"
    )
async def slash_shutdown(interaction:discord.Interaction) -> None:
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    await interaction.response.send_message("Shutting down.", ephemeral=True)
    bot_logger.debug("shutdown by command.")
    save_logs()
    await bot.close()
    await client.close()
    sys.exit()

@register
def terminate() -> None: 
    bot_logger.info("Logging off")
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
    asyncio.run(main())
