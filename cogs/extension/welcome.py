import logging
import json
import os

import discord
from discord.ext import commands
from discord import app_commands

import config
import dragon_database

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.logger = logging.getLogger("winter_dragon.welcome")
        self.data = None
        self.DATABASE_NAME = "Welcome"
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME} Json Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        else:
            with open(self.DBLocation, "r") as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "w") as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.data:
            self.data = await self.get_data()

    async def cog_unload(self):
        await self.set_data(self.data)

    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        channel = member.guild.system_channel
        if not self.data[str(member.guild.id)]["enabled"]:
            return
        if channel is not None and config.Welcome.DM == False:
            await channel.send(f"Welcome {member.mention} to {member.guild}")
        elif channel is not None and config.Welcome.DM == True and member.bot == False:
            dm = await member.create_dm()
            await dm.send(f"Welcome {member.mention} to {member.guild}, you may use `/help` to see what commands i have!")
        else:
            self.logger.warning("No system_channel to welcome user to, and dm is disabled.")

    @app_commands.command(
        name="enable",
        description="Enable welcome message"
    )
    async def slash_enable(self, interaction:discord.Interaction):
        self.data[str(interaction.guild.id)] = {"enabled":True}

    @app_commands.command(
        name="disable",
        description="Disable welcome message"
    )
    async def slash_enable(self, interaction:discord.Interaction):
        self.data[str(interaction.guild.id)] = {"enabled":False}

async def setup(bot:commands.Bot):
	await bot.add_cog(Welcome(bot))
