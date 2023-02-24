import contextlib
import datetime
import pickle
import logging
import os
import random

import discord
import num2words
from discord import app_commands
from discord.ext import commands, tasks

import config
import dragon_database
import rainbow

# TODO: Make time based system with reply to original message
# mentioning the winning poll
# TODO: Add suggestions with dedicated channel etc.
# Rewrite?
class Poll(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = await self.get_data()
        if config.Database.PERIODIC_CLEANUP:
            self.cleanup.start()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    @tasks.loop(seconds=3600)
    async def cleanup(self) -> None:
        if not self.data:
            self.data = await self.get_data()
        self.logger.info("Cleaning poll database")
        if not self.data:
            return
        for k, v in list(self.data.items()):
            if v["Time"] <= datetime.datetime.now().timestamp():
                del self.data[k]
        await self.set_data(self.data)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, user:discord.Member) -> None:
        if user.bot == True:
            return
        if not self.data:
            self.data = await self.get_data()
        if str(reaction.message.id) not in self.data:
            return
        UsersList = self.data[str(reaction.message.id)]["Users"]
        time:int = self.data[str(reaction.message.id)]["Time"]
        if user.id not in UsersList and time >= datetime.datetime.now().timestamp():
            UsersList.append(user.id)
        else:
            await reaction.remove(user)
            dm = await user.create_dm()
            await dm.send("Your new reaction has been removed from the vote.\n You cannot for something else.")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction:discord.Reaction, user:discord.Member|discord.User) -> None:
        if not self.data:
            self.data = await self.get_data()
        with contextlib.suppress(KeyError):
            UsersList = self.data[str(reaction.message.id)]["Users"]
        if user.id in UsersList and UsersList.count(user.id) >= 2:
            UsersList.remove(user.id)

    @app_commands.command(
        name = "create",
        description = "Send a poll to ask users questions. use: , (comma) to seperate each option"
        )
    @app_commands.guild_only()
    async def slash_poll(self, interaction:discord.Interaction, time_in_sec:int, question:str, *, options:str) -> None:
        if interaction.user.guild_permissions.administrator != True:
            return
        if not self.data:
            self.data = await self.get_data()
        emb = discord.Embed(title="Poll", description=f"{question}", color=random.choice(rainbow.RAINBOW))
        emb.timestamp = datetime.datetime.now()
        date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=time_in_sec)).timestamp()
        epoch = int(date)
        options:list = options.split(sep=",")
        for i, option in enumerate(options):
            if i >= 10:
                await interaction.response.send_message("Only 10 options are supported", ephemeral=True)
                break
            clean_option = option.strip()
            emb.add_field(name=f":{num2words.num2words(i+1)}:", value=clean_option, inline=True)
        emb.add_field(name="Time-out", value=f"<t:{epoch}:R>", inline=False)
        msg:discord.Message = await interaction.response.send_message(embed=emb)
        self.data[str(msg.id)] = {"Time":epoch, "Question": question, "Options":options, "Users":[]}
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
        await self.set_data(self.data)

async def setup(bot:commands.Bot) -> None:
	await bot.add_cog(Poll(bot))
