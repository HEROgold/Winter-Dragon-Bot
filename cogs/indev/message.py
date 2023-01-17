import json
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database

# TODO: create commands: message ranks, message query
# message query should try and count all the times a user said the query
# message ranks should count the top 10 most said words
# TODO: Add statistics to show to players for message ranks

class Messages(commands.GroupCog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.database_name = "Message"
        self.logger = logging.getLogger("winter_dragon.message")
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

    async def get_data(self) -> dict[str, dict[str, dict[str, str]]]:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @app_commands.command(
        name = "get",
        description = f"get and store the last {config.Message.LIMIT} messages, in each channel from this server!"
        )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 300)
    async def slash_get_message(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        await self.get_message(interaction, guild)
        await interaction.followup.send("Updated my database!", ephemeral=True)
        self.logger.info("Finished updating messages")

    @app_commands.command(
        name = "get_all",
        description = f"get and store the last {config.Message.LIMIT} messages, in each channel from each server!"
        )
    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    async def slash_mass_get__message(self, interaction:discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        for guild in self.bot.guilds:
            await self.get_message(interaction, guild)
        await interaction.followup.send("Updated my database!", ephemeral=True)
        self.logger.info("Finished updating messages")

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if not message.guild or message.content == "":
            return
        self.logger.debug(f"Collecting message: member='{message.author}', id='{message.id}' content='{message.content}'")
        guild = message.guild
        guild_id = str(guild.id)
        channel = message.channel
        channel_id = str(channel.id)
        data = await self.get_data()
        data[guild_id][channel_id][str(message.id)] = {"member_id":str(message.author.id), "content":str(message.content)}
        await self.set_data(data)

    async def get_message(self, interaction:discord.Interaction, guild:discord.Guild=None) -> None:
        data = await self.get_data()
        guild_id = str(guild.id)
        if guild_id not in data:
            data[guild_id] = {}
        for channel in interaction.guild.channels:
            if channel.type in [discord.ChannelType.category, discord.ChannelType.forum]:
                continue
            channel_id = str(channel.id)
            if channel_id not in data[guild_id]:
                data[guild_id][channel_id] = {}
            self.logger.debug(f"Getting messages from: guild='{guild}, channel='{channel}'")
            async for message in channel.history(limit=config.Message.LIMIT):
                if str(message.id) in data[guild_id][channel_id]:
                    break
                if message.content in ["", "[Original Message Deleted]"]:
                    # Skip empty contents (I.e. Bot embeds etc.)
                    continue
                data[guild_id][channel_id][str(message.id)] = {"member_id":str(message.author.id), "content":str(message.content)}
            if not data[guild_id][channel_id]:
                # Clean-up data if channel has no messages.
                del data[guild_id][channel_id]
        await self.set_data(data)

async def setup(bot:commands.Bot):
    await bot.add_cog(Messages(bot))
