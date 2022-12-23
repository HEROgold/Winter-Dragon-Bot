import contextlib
import logging
import discord
import datetime
import json
import os
import asyncio
from discord.ext import commands
from discord import app_commands
import num2words


class Poll(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot:commands.bot = bot
        self.check_database()
        asyncio.get_running_loop().create_task(self.clean_up())

    def check_database(self):
        if not os.path.exists('./Database/Poll.json'):
            with open("./Database/Poll.json", "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                logging.info("Poll Json Created.")
        else:
            logging.info("Poll Json Loaded.")

    async def clean_up(self) -> None:
        while True:
            data = await self.get_data()
            for k, v in list(data.items()):
                if v["Time"] <= datetime.datetime.now().timestamp():
                    del data[k]
            await self.set_data(data)
            await asyncio.sleep(60*60)

    async def get_data(self) -> dict:
        with open('.\\Database/Poll.json', 'r') as f:
            data = json.load(f)
        return data

    async def set_data(self, data) -> None:
        with open('.\\Database/Poll.json','w') as f:
            json.dump(data, f)

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

    @app_commands.command(name = "poll", description="Send a poll to ask users questions")
    async def slash_poll(self, interaction:discord.Interaction, time_in_sec:int, question:str, *, options:str):
        if interaction.user.guild_permissions.administrator != True:
            return
        await interaction.response.defer()
        data = await self.get_data()
        emb = discord.Embed(title="Poll", description=f"{question}", colour=0xff5511)
        emb.timestamp = datetime.datetime.now()
        date = (datetime.datetime.now() + datetime.timedelta(seconds=time_in_sec)).timestamp()
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
            allowed_emojis = [
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
            await msg.add_reaction(allowed_emojis[i])

async def setup(bot:commands.Bot):
	await bot.add_cog(Poll(bot))