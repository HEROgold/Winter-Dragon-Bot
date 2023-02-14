import asyncio
import logging
import os
from atexit import register

import discord
from discord import app_commands
from discord.ext import commands

import config

# Change values/settings in config.py.
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
# discord_bot_logger.addHandler(logging.StreamHandler())

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

# FIXME: find a way to get guild OBJECT without await and after bot is ready
# TODO: move commands to support only server/guild
# support_guild = asyncio.run(bot.fetch_guild(config.Main.SUPPORT_GUILD_ID))
support_guild = discord.utils.get(bot.guilds, id=config.Main.SUPPORT_GUILD_ID)

# Define empty vars for checks.
ar = None

bot_logger.debug(f"Support guild id: {support_guild}")

if config.Main.CUSTOM_HELP:
    bot.remove_command("help")

@bot.event
async def on_ready():
    print("Bot is running!")
    if config.Main.SHOW_LOGGED_IN == True:
        bot_logger.info(f'Logged on as {bot.user}!')

async def main():
    async with bot:
        await mass_load()
        await bot.start(config.Main.TOKEN)

@register
def terminate():
    # Client.close unloads cogs first.
    asyncio.run(client.close())
    bot_logger.info("Logged off")

async def get_cogs() -> list[str]:
    extensions = []
    for root, subdirs, files in os.walk("cogs"):
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
            bot_logger.exception(f"Error while loading {cog}")
    if not (os.listdir("./cogs")):
        bot_logger.warning("No Cogs Directory To Load!")

@tree.command(
    name = "shutdown",
    description = "(For bot developer only)",
    guild = support_guild
    )
async def slash_shutdown(interaction:discord.Interaction, extension:str):
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    await interaction.response.send_message("Shutting down...",ephemeral=True)
    terminate()


#run the bot!
if __name__ == "__main__":
    asyncio.run(main())
