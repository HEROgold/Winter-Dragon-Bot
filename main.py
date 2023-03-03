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

Intents = discord.Intents.default()
# Intents = discord.Intents.all()
Intents.members = True
Intents.guilds = True
Intents.presences = True
# Intents.guild_messages = True
# Intents.dm_messages = True
Intents.moderation = True
Intents.messages = True
Intents.message_content = True
Intents.auto_moderation_configuration = True
Intents.auto_moderation_execution = True

client = discord.Client(intents=Intents)
bot = commands.Bot(intents=Intents, command_prefix=commands.when_mentioned_or(config.Main.PREFIX), case_insensitive=True)
tree = bot.tree

# FIXME: find a way to get/fetch guild OBJECT without await and before bot is starting/ready
# support_guild = asyncio.run(bot.fetch_guild(config.Main.SUPPORT_GUILD_ID))
# support_guild = await bot.fetch_guild(config.Main.SUPPORT_GUILD_ID)
support_guild = discord.utils.get(bot.guilds, id=config.Main.SUPPORT_GUILD_ID)


bot_logger.debug(f"Support guild id: {support_guild}")

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
        await bot.start(config.Main.TOKEN)

@register
def terminate() -> None:
    # Client.close unloads cogs.
    try:
        asyncio.run(client.close())
    except Exception as e:
        bot_logger.warning(f"Likely shutdown command: {e}")
    bot_logger.info("Logged off")
    if not os.path.exists(config.Main.LOG_PATH):
        os.mkdir(config.Main.LOG_PATH)
    log_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    if not os.path.exists(f"{config.Main.LOG_PATH}/{log_time}"):
        os.mkdir(f"{config.Main.LOG_PATH}/{log_time}")
    bot_logger.info("Saved log files")
    shutil.copy(src="bot.log", dst=f"{config.Main.LOG_PATH}/{log_time}/bot_.log")
    shutil.copy(src="discord.log", dst=f"{config.Main.LOG_PATH}/{log_time}/discord_.log")

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
        except Exception:
            bot_logger.exception(f"Error while loading {cog}")
    if not (os.listdir("./cogs")):
        bot_logger.warning("No Cogs Directory To Load!")

@tree.command(
    name = "shutdown",
    description = "(For bot developer only)",
    guild = support_guild
    )
async def slash_shutdown(interaction:discord.Interaction) -> None:
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    await interaction.response.send_message("Shutting down...",ephemeral=True)
    terminate()
    await client.close()
    sys.exit()

#run the bot!
if __name__ == "__main__":
    asyncio.run(main())
