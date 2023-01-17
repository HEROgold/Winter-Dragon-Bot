import asyncio
import logging
import os
import traceback

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database


# We make use of a config.Main file, change values in config.Main.py.
# TODO: Push owner only commands in specific guild.

LOG_LEVEL = logging.DEBUG

bot_logger = logging.getLogger("winter_dragon")
discord_logger = logging.getLogger('discord')

bot_logger.setLevel(LOG_LEVEL)
bot_handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
bot_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
bot_logger.addHandler(bot_handler)
bot_logger.addHandler(logging.StreamHandler())

discord_logger.setLevel(LOG_LEVEL)
discord_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
discord_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
discord_logger.addHandler(discord_handler)    
# discord_logger.addHandler(logging.StreamHandler())

Intents = discord.Intents.default()
# Intents = discord.Intents.all()
Intents.members = True
Intents.presences = True
Intents.message_content = True
Intents.auto_moderation_configuration = True
Intents.auto_moderation_execution = True

client = discord.Client(intents=Intents)
bot = commands.Bot(intents=Intents, command_prefix=commands.when_mentioned_or(config.Main.PREFIX), case_insensitive=True)
tree = bot.tree

support_guild = bot.get_guild(config.Main.SUPPORT_GUILD_ID)

if config.Main.CUSTOM_HELP:
    bot.remove_command("help")

@bot.event
async def on_ready():
    # Rename not needed
    # bot_username = await bot.user.edit(username="Winter Dragon")
    # bot_logger.info(f"Username updated to {bot_username}")
    print("Bot is running!")
    if config.Main.SHOW_LOGGED_IN == True:
        bot_logger.info(f'Logged on as {bot.user}!')

async def innit():
    await mass_load_cogs()
    DB = dragon_database.Database()
    await DB.get_client()

async def get_cogs() -> list[str]:
    extensions = []
    for root, subdirs, files in os.walk("cogs"):
        extensions.extend(
            os.path.join(root, file[:-3]).replace("\\", ".")
            for file in files
            if file.endswith(".py")
        )
    return extensions

async def mass_load_cogs() -> None:
    cogs = await get_cogs()
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            bot_logger.info(f"Loaded {cog}")
        except Exception as e:
            bot_logger.exception(f"Error while loading {cog}")
    if not (os.listdir("./cogs")):
        bot_logger.warning("No Cogs Directory To Load!")

async def mass_reload_cogs(interaction:discord.Interaction):
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

@tree.command(
    name = "show_cogs",
    description= "Show loaded cogs (For bot developer only)",
    guild = support_guild
    )
async def slash_show_cogs(interaction:discord.Interaction):
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    cogs = await get_cogs()
    bot_logger.debug(f"Showing {cogs} to {interaction.user}")
    await interaction.response.send_message(f"{cogs}", ephemeral=True)

@tree.command(
    name = "reload",
    description = "Reload a specified or all available cogs (For bot developer only)",
    guild = support_guild
    )
async def slash_restart(interaction:discord.Interaction, extension:str):
    if not await bot.is_owner(interaction.user):
        raise commands.NotOwner
    await interaction.response.defer()
    if extension is None :
        await mass_reload_cogs(interaction)
    else:
        try:
            await bot.reload_extension(extension)
            bot_logger.info(f"Reloaded {extension}")
            await interaction.followup.send(f"Reloaded {extension}", ephemeral=True)
        except Exception:
            await interaction.followup.send(f"error reloading {extension}: {traceback.print_exc()}", ephemeral=True)

@slash_restart.autocomplete("extension")
async def restart_autocomplete_extension(interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=extension, value=extension)
        for extension in bot.extensions
        if current.lower() in extension.lower()
    ]

@tree.command(
    name = "unload",
    description = "Unload a specified cog (For bot developer only)",
    guild = support_guild
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

@tree.command(
    name = "load",
    description = "Load a specified or all available cogs (For bot developer only)",
    guild = support_guild
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

async def main():
    async with bot:
        await innit()
        await bot.start(config.Main.TOKEN)

#run the bot!
if __name__ == "__main__":
    asyncio.run(main())
