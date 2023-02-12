import asyncio
import contextlib
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from atexit import register

import config
import dragon_database


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
    with contextlib.suppress(commands.errors.ExtensionNotLoaded):
        asyncio.run(mass_unload())
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

async def mass_unload() -> None:
    cogs = await get_cogs()
    for cog in cogs:
        try:
            await bot.unload_extension(cog)
            bot_logger.info(f"Unloaded {cog}")
        except Exception as e:
            bot_logger.exception(f"Error while unloading {cog}")
    if not (os.listdir("./cogs")):
        bot_logger.warning("No Cogs Directory To Unload!")

async def mass_reload(interaction:discord.Interaction) -> None:
    reload_message = ""
    cogs = await get_cogs()
    for cog in cogs:
        try:
            bot.reload_extension(cog)
        except Exception as e:
            bot_logger.exception(f"Error while reloading {cog}")
        bot_logger.info(f"Reloaded {cog}")
        reload_message += f"Reloaded {cog}\n"
    await interaction.followup.send(f"{reload_message}Restart complete.")

# @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
@app_commands.command(
    name = "show",
    description= "Show loaded cogs (For bot developer only)"
    )
async def slash_show_cogs(interaction:discord.Interaction):
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    cogs = await get_cogs()
    bot_logger.debug(f"Showing {cogs} to {interaction.user}")
    await interaction.response.send_message(f"{cogs}", ephemeral=True)

# @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
@app_commands.command(
    name = "reload",
    description = "Reload a specified or all available cogs (For bot developer only)"
    )
async def slash_restart(interaction:discord.Interaction, extension:str):
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    await interaction.response.defer()
    if extension is None :
        await mass_reload(interaction)
    else:
        try:
            await bot.reload_extension(extension)
            bot_logger.info(f"Reloaded {extension}")
            await interaction.followup.send(f"Reloaded {extension}", ephemeral=True)
        except Exception:
            await interaction.followup.send(f"error reloading {extension}", ephemeral=True)

@slash_restart.autocomplete("extension")
async def restart_autocomplete_extension(interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=extension, value=extension)
        for extension in bot.extensions
        if current.lower() in extension.lower()
    ]

# @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
@app_commands.command(
    name = "unload",
    description = "Unload a specified cog (For bot developer only)"
    )
async def slash_unload(interaction:discord.Interaction, extension:str):
    if not bot.is_owner(interaction.user):
        raise commands.NotOwner
    await interaction.response.defer(ephemeral=True)
    if extension is None:
        await interaction.followup.send("Please provide a cog to unload.", ephemeral=True)
    else:
        try:
            await bot.unload_extension(extension)
            bot_logger.info(f"Unloaded {extension}")
            await interaction.followup.send(f"Unloaded {extension}", ephemeral=True)
        except Exception:
            bot_logger.warning(f"unable to reload {extension}")
            await interaction.followup.send(f"Unable to reload {extension}", ephemeral=True)

@slash_unload.autocomplete("extension")
async def restart_autocomplete_extension(interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=extension, value=extension)
        for extension in bot.extensions
        if current.lower() in extension.lower()
    ]

# @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
@app_commands.command(
    name = "load",
    description = "Load a specified or all available cogs (For bot developer only)"
    )
async def slash_load(interaction:discord.Interaction, extension:str):
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    await interaction.response.defer(ephemeral=True)
    try:
        await bot.load_extension(extension)
        bot_logger.info(f"Loaded {extension}")
        await interaction.followup.send(f"Loaded {extension}", ephemeral=True)
    except Exception:
        bot_logger.warning(f"unable to load {extension}")
        await interaction.followup.send(f"Unable to load {extension}", ephemeral=True)

@slash_load.autocomplete("extension")
async def restart_autocomplete_extension(interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    cogs = await get_cogs()
    return [
        app_commands.Choice(name=extension, value=extension)
        for extension in cogs
        if current.lower() in extension.lower()
    ]

#run the bot!
if __name__ == "__main__":
    asyncio.run(main())
