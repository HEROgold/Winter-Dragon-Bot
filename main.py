import discord
from discord.ext import commands
import logging
import os
import mainconfig

# We make use of a config file, change values in mainconfig.py.

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
intents = discord.Intents.default()
intents.members, intents.presences = True, True

client = discord.Client()
bot = commands.Bot(intents=intents, command_prefix=commands.when_mentioned_or(mainconfig.prefix), case_insensitive=True)
bot.remove_command("help")

@bot.event
async def on_ready(): # logged in?
    bot_username = await bot.user.edit(username="Winter Dragon")
    if mainconfig.show_logged_in == True:
        print(f"Username changed to {0}".format(bot_username))
        print('Logged on as {0}!'.format(bot.user))

@bot.event
async def on_message(ctx): # simple chat logger
    if mainconfig.log_messages == True:
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
    print("No Cogs To Load!")

@bot.command(aliases=["reload", "restart"]) # show some guild/server stats
async def _restart(ctx, extension= None):
    if ctx.message.author.id == 216308400336797706:
        if extension == None:
            for root, subdirs, files in os.walk("cogs"):
                for file in files:
                    if file.endswith(".py"):
                        extension = os.path.join(root, file[:-3]).replace("\\", ".")
                        try:
                            bot.reload_extension(extension)
                        except:
                            print({0})
                            pass
                        print(f"Reloaded {extension}")
                        await ctx.send(f"Reloaded {extension}")
            await ctx.send(f"Restarted.")
        else:
            bot.reload_extension(extension)
            print(f"Reloaded {extension}")
            await ctx.send(f"Reloaded {extension}")
    else:
        await ctx.send("You are not allowed to use this command.")

#run the bot!
bot.run("NzQyNzc3NTk2NzM0OTk2NTgy.XzLDiw.MwccdvHGJkp85TDsRmoEXDBEoiY")