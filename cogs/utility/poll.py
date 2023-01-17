import asyncio
import contextlib
import datetime
import json
import logging
import os
import random

import discord
import num2words
from discord import app_commands
from discord.ext import commands

import config
import dragon_database
import rainbow

# TODO: Make time based system with reply to original message
# mentioning the winning poll
class Poll(commands.GroupCog):
    def __init__(self, bot:commands.Bot):
        super().__init__()
        self.bot:commands.bot = bot
        self.database_name = "Poll"
        self.logger = logging.getLogger("winter_dragon.poll")
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.database_name}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                self.logger.debug(f"{self.database_name} Json Created.")
        else:
            self.logger.debug(f"{self.database_name} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        print(data)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.cleanup()

    async def cleanup(self):
        data = await self.get_data()
        self.logger.debug("Cleaning poll database")
        if not data:
            return
        for k, v in list(data.items()):
            if v["Time"] <= datetime.datetime.now().timestamp():
                del data[k]
        await self.set_data(data)
        await asyncio.sleep(60*60)
        if config.Database.PERIODIC_CLEANUP:
            await self.cleanup()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, user:discord.Member):
        if user.bot == True:
            return
        data = await self.get_data()
        if str(reaction.message.id) not in data:
            return
        UsersList:list = data[str(reaction.message.id)]["Users"]
        time:int = data[str(reaction.message.id)]["Time"]
        if user.id not in UsersList and time >= datetime.datetime.now().timestamp():
            UsersList.append(user.id)
            await self.set_data(data)
        else:
            await reaction.remove(user)
            dm = await user.create_dm()
            await dm.send("Your new reaction has been removed from the vote.\n You cannot for something else.")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction:discord.Reaction, user:discord.Member|discord.User):
        data = await self.get_data()
        with contextlib.suppress(KeyError):
            UsersList:list = data[str(reaction.message.id)]["Users"]
        if user.id in UsersList and UsersList.count(user.id) >= 2:
            UsersList.remove(user.id)
        await self.set_data(data)

    @app_commands.command(
        name = "create",
        description = "Send a poll to ask users questions. use `,` to seperate each option"
        )
    @app_commands.guild_only()
    async def slash_poll(self, interaction:discord.Interaction, time_in_sec:int, question:str, *, options:str):
        if interaction.user.guild_permissions.administrator != True:
            return
        await interaction.response.defer()
        data = await self.get_data()
        emb = discord.Embed(title="Poll", description=f"{question}", color=random.choice(rainbow.RAINBOW))
        emb.timestamp = datetime.datetime.now()
        date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=time_in_sec)).timestamp()
        epoch = int(date)
        options:list = options.split(sep=",")
        for i, option in enumerate(options):
            if i >= 10:
                await interaction.followup.send("Only 10 options are supported", ephemeral=True)
                break
            clean_option = option.strip()
            emb.add_field(name=f":{num2words.num2words(i+1)}:", value=clean_option, inline=True)
        emb.add_field(name="Time-out", value=f"<t:{epoch}:R>", inline=False)
        msg:discord.Message = await interaction.followup.send(embed=emb)
        data[str(msg.id)] = {"Time":epoch, "Question": question, "Options":options, "Users":[]}
        await self.set_data(data)
        for i, option in enumerate(options):
            if i >= 10:
                break
            ALLOWED_EMOJIS = [
                "1️⃣",
                "2️⃣",
                "3️⃣",
                "4️⃣",
                "5️⃣",
                "6️⃣",
                "7️⃣",
                "8️⃣",
                "9️⃣",
                "🔟",
            ]
            await msg.add_reaction(ALLOWED_EMOJIS[i])

async def setup(bot:commands.Bot):
	await bot.add_cog(Poll(bot))
