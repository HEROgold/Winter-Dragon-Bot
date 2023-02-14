
import logging
import json
import os

import discord
from discord.ext import commands
from discord import app_commands

import config
import dragon_database

class Welcome(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")
        self.data = None
        # self.data = {"DUMMY_GUILD_ID":{"enabled":True}}
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
            self.setup_json()

    def setup_json(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = self.data
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

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "w") as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.data:
            self.data = await self.get_data()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member) -> None:
        if not self.data:
            self.data = await self.get_data()
        enabled = self.data[str(member.guild.id)]["enabled"]
        if not enabled:
            return
        channel = member.guild.system_channel
        default_msg = f"Welcome {member.mention} to {member.guild},\nyou may use `/help` to see what commands I have!"
        custom_msg = self.data[str(member.guild.id)]["message"]
        if channel is not None and config.Welcome.DM == False:
            if custom_msg:
                await channel.send(custom_msg)
            else:
                await channel.send(default_msg)
        elif channel is not None and config.Welcome.DM == True and member.bot == False:
            dm = await member.create_dm()
            if custom_msg:
                await dm.send(custom_msg)
            else:
                await dm.send(default_msg)
        else:
            self.logger.warning("No system_channel to welcome user to, and dm is disabled.")

    @app_commands.guild_only()
    @app_commands.command(
        name="enable",
        description="Enable welcome message"
    )
    async def slash_enable(self, interaction:discord.Interaction) -> None:
        self.data = {
            str(interaction.guild.id): {
                "enabled" : True
                }
        }
        await interaction.response.send_message("Enabled welcome message.", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(
        name="disable",
        description="Disable welcome message"
    )
    async def slash_disable(self, interaction:discord.Interaction) -> None:
        self.data = {
            str(interaction.guild.id): {
                "enabled" : False
                }
        }
        await interaction.response.send_message("Disabled welcome message.", ephemeral=True)

    @app_commands.command(
        name="message",
        description="set the welcome message for your guild"
    )
    async def slash_message(self, interaction:discord.Interaction, message:str) -> None:
        self.data = {
            str(interaction.guild.id): {
                "message" : message
                }
        }
        await interaction.response.send_message(f"Changed welcome message to\n{message}.", ephemeral=True)
        await self.set_data(self.data)

async def setup(bot:commands.Bot) -> None:
    # sourcery skip: instance-method-first-arg-name
	await bot.add_cog(Welcome(bot))
