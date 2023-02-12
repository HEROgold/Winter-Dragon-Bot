import asyncio
import logging
import os
import traceback

import discord
from discord import app_commands
from discord.ext import commands
from atexit import register

import config
import dragon_database


# We make use of a config.Main file, change values in config.Main.py.
# TODO: Push owner only commands in specific guild.
# TODO: check all commands for correct permissions checks!

LOG_LEVEL = logging.DEBUG

bot_logger = logging.getLogger("winter_dragon")
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
# discord_logger.addHandler(logging.StreamHandler())

Intents = discord.Intents.default()
# Intents = discord.Intents.all()
Intents.members = True
Intents.guilds = True
Intents.presences = True
# Intents.guild_messages = True
# Intents.dm_messages = True
Intents.messages = True
Intents.message_content = True
Intents.auto_moderation_configuration = True
Intents.auto_moderation_execution = True

client = discord.Client(intents=Intents)
bot = commands.Bot(intents=Intents, command_prefix=commands.when_mentioned_or(config.Main.PREFIX), case_insensitive=True)
tree = bot.tree

if config.Main.CUSTOM_HELP:
    bot.remove_command("help")

async def innit():
    db = dragon_database.Database()
    await db.get_client()

@bot.event
async def on_ready():
    print("Bot is running!")
    if config.Main.SHOW_LOGGED_IN == True:
        bot_logger.info(f'Logged on as {bot.user}!')

async def main():
    async with bot:
        await innit()
        await bot.load_extension("cogs.extension.cogs_control")
        await bot.start(config.Main.TOKEN)

@register
def terminate():
    bot_logger.info("Logging off")
    asyncio.run(client.close())

#run the bot!
if __name__ == "__main__":
    asyncio.run(main())
