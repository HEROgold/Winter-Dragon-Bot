import discord
from discord.ext import commands
import logging
import os
from config import main as config

# We make use of a config file, change values in config.py.

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
intents = discord.Intents.default()
intents.members, intents.presences = True, True

client = discord.Client()
bot = commands.Bot(intents=intents, command_prefix=commands.when_mentioned_or(config.prefix), case_insensitive=True)
#bot.remove_command("help")

@bot.event
async def on_ready(): # logged in?
    bot_username = await bot.user.edit(username="Winter Dragon")
    if config.show_logged_in == True:
        print(f"Username changed to {bot_username}")
        print('Logged on as {bot.user}!')

@bot.event
async def on_message(ctx): # simple chat logger
    if config.log_messages == True:
        print(f'Message from {ctx.author}: {ctx.content}')
    await bot.process_commands(ctx)

for root, subdirs, files in os.walk("cogs"): #load all needed cogs/classes/commands
    for file in files:
        if file.endswith(".py"):
            try:
                extension = os.path.join(root, file[:-3]).replace("\\", ".")
                bot.load_extension(extension)
                print(f"Loaded {extension}")
            except:
                print(f"Error while loading {extension}")
        else:
            print(f"Unable to load {file}, it is not a .py file.")
if not (os.listdir("./cogs")):
    print("No Cogs Directory To Load!")

@bot.command()
async def show_cogs(ctx):
    cogs = []
    for root, subdirs, files in os.walk("cogs"):
        for file in files:
            if file.endswith(".py"):
                extension = os.path.join(root, file[:-3]).replace("\\", ".")
                print(f"Showing {extension} to {ctx.author}")
                cogs.append(extension)
    dm = await ctx.author.create_dm()
    await dm.send(cogs)

@bot.command(aliases=["reload", "restart"]) # reload all available cogs.
async def _restart(ctx, extension=None):
    if ctx.message.author.id == config.owner_id:
        if extension == None:
            for root, subdirs, files in os.walk("cogs"):
                for file in files:
                    if file.endswith(".py"):
                        extension = os.path.join(root, file[:-3]).replace("\\", ".")
                        extensions = []
                        try:
                            bot.reload_extension(extension)
                            extensions.append(extension)
                        except:
                            print({0})
                            pass
                        print(f"Reloaded {extension}")
                    await ctx.send(f"Reloaded {extensions}")
            await ctx.send(f"Restarted.")
        else:
            try:
                bot.reload_extension(extension)
                print(f"Reloaded {extension}")
                await ctx.send(f"Reloaded {extension}")
            except:
                await ctx.send(f"error reloading {extension}")
    else:
        await ctx.send("You are not allowed to use this command.")

@bot.command()
async def unload(ctx, extension=None): # unload specific cog
    if ctx.message.author.id == config.owner_id:
        if extension == None:
            await ctx.send("Please provide a cog to unload.")
        else:
            try:
                bot.unload_extension(extension)   
                print(f"Unloaded {extension}")
                await ctx.send(f"Unloaded {extension}")
            except:
                print(f"unable to reload {extension}")
                await ctx.send(f"Unable to reload {extension}")
    else:
        await ctx.send("You are not allowed to use this command.")

@bot.command()
async def load(ctx, extension=None): # Load specific Cog
    if ctx.message.author.id == config.owner_id:
        if extension == None:
            await ctx.send("Please provide a cog to load.")
        else:
            try:
                bot.load_extension(extension)   
                print(f"Loaded {extension}")
                await ctx.send(f"Loaded {extension}")
            except:
                print(f"unable to load {extension}")
                await ctx.send(f"Unable to load {extension}")
    else:
        await ctx.send("You are not allowed to use this command.")

#run the bot!
bot.run(config.token)