import asyncio
import discord
from discord.ext import commands
import logging
import os
from config import main as config
import traceback
# We make use of a config file, change values in config.py.

LOG_LEVEL = logging.INFO

bot_logger = logging.getLogger()
bot_logger.setLevel(LOG_LEVEL)
bot_handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
bot_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
bot_logger.addHandler(bot_handler)

discord_log = logging.getLogger('discord')
discord_log.setLevel(LOG_LEVEL)
discord_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
discord_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
discord_log.addHandler(discord_handler)    

Intents = discord.Intents.default()
# Intents = discord.Intents.all()
Intents.members = True
Intents.presences = True
Intents.message_content = True
Intents.auto_moderation_configuration = True
Intents.auto_moderation_execution = True

client = discord.Client(intents=Intents)
bot = commands.Bot(intents=Intents, command_prefix=commands.when_mentioned_or(config.prefix), case_insensitive=True)

if config.enable_custom_help:
    bot.remove_command("help")

@bot.event
async def on_ready():
    bot_username = await bot.user.edit(username="Winter Dragon")
    print("Bot is running!")
    logging.info(f"Username updated to {bot_username}")
    if config.show_logged_in == True:
        logging.info(f'Logged on as {bot.user}!')

async def innit():
    await mass_load_cogs()

async def get_cogs() -> list:
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
            logging.info(f"Loaded {cog}")
        except Exception as e:
            logging.warning(f"Error while loading {cog}: {traceback.print_exc()}")
    if not (os.listdir("./cogs")):
        logging.warning("No Cogs Directory To Load!")

@bot.command(description = "Show all currently loaded cogs in a list format",
            brief = "Show loaded cogs(For bot developer only)",
            usage = "`show_cogs`")
async def show_cogs(ctx:commands.Context):
    if ctx.message.author.id != config.owner_id and not await bot.is_owner(ctx.message.author):
        return
    cogs = get_cogs()
    logging.info(f"Showing {cogs} to {ctx.author}")
    dm = await ctx.author.create_dm()
    await dm.send(cogs)

@bot.command(aliases=["reload", "restart"],
            description = "Reload a specified or all available cogs",
            brief = "Reload cogs (For bot developer only)",
            usage = "`reload [cog]`:\n Examples: `reload cogs.extension.error`,\n`reload`")
async def _restart(ctx:commands.Context, extension=None):
    if ctx.message.author.id != config.owner_id and not await bot.is_owner(ctx.message.author):
        await ctx.send("You are not allowed to use this command.")
        return
    if extension is None:
        await mass_reload_cogs(ctx)
    else:
        try:
            bot.reload_extension(extension)
            logging.info(f"Reloaded {extension}")
            await ctx.send(f"Reloaded {extension}")
        except Exception:
            await ctx.send(f"error reloading {extension}: {traceback.print_exc()}")

async def mass_reload_cogs(ctx:commands.Context):
    reload_message = ""
    cogs = await get_cogs()
    for cog in cogs:
        try:
            bot.reload_extension(cog)
        except Exception as e:
            logging.warning(f"Error while reloading {cog}: {traceback.print_exc()}")
        logging.info(f"Reloaded {cog}")
        reload_message += f"Reloaded {cog}\n"
    await ctx.send(f"{reload_message}Restart complete.")

@bot.command(description = "Unload a specified cog",
            brief = "Unload cogs (For bot developer only)",
            usage = "`reload [cog]`:\n Examples: `reload cogs.extension.error`")
async def unload(ctx:commands.Context, extension=None):
    if ctx.message.author.id == config.owner_id or bot.is_owner(ctx.message.author):
        if extension is None:
            await ctx.send("Please provide a cog to unload.")
        else:
            try:
                bot.unload_extension(extension)
                logging.info(f"Unloaded {extension}")
                await ctx.send(f"Unloaded {extension}")
            except Exception:
                logging.warning(f"unable to reload {extension}")
                await ctx.send(f"Unable to reload {extension}")
    else:
        await ctx.send("You are not allowed to use this command.")

@bot.command(description = "Load a specified or all available cogs",
            brief = "Load cogs (For bot developer only)",
            usage = "`Load [cog]`:\n Examples: `load cogs.extension.error`")
async def load(ctx:commands.Context, extension=None):
    if ctx.message.author.id == config.owner_id or await bot.is_owner(ctx.message.author):
        if extension is None:
            await ctx.send("Please provide a cog to load.")
        else:
            try:
                bot.load_extension(extension)
                logging.info(f"Loaded {extension}")
                await ctx.send(f"Loaded {extension}")
            except Exception:
                logging.warning(f"unable to load {extension}")
                await ctx.send(f"Unable to load {extension}")
    else:
        await ctx.send("You are not allowed to use this command.")

async def main():
    async with bot:
        await innit()
        await bot.start(config.token)

#run the bot!
if __name__ == "__main__":
    asyncio.run(main())
