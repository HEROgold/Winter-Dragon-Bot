import pickle
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import config
from tools import dragon_database_Mongo

# TODO: create commands: message ranks, message query
# message query should try and count all the times a user said the query
# message ranks should count the top 10 most said words
# TODO: Add statistics (graphs?) to show to players for message ranks


class Messages(commands.GroupCog):
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

    def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database_Mongo.Database()
            data = db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database_Mongo.Database()
            db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = self.get_data()

    async def cog_unload(self) -> None:
        self.set_data(self.data)

    @app_commands.command(
        name = "get",
        description = f"get and store the last {config.Message.LIMIT} messages, in each channel from this server!"
        )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 300)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def slash_get_message(self, interaction:discord.Interaction) -> None:
        guild = interaction.guild
        await self.get_message(interaction, guild)
        await interaction.response.send_message("Updated my database!", ephemeral=True)
        self.logger.info("Finished updating messages")

    @app_commands.command(
        name = "get_all",
        description = f"get and store the last {config.Message.LIMIT} messages, in each channel from each server!"
        )
    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    async def slash_mass_get__message(self, interaction:discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        for guild in self.bot.guilds:
            await self.get_message(interaction, guild)
        await interaction.response.send_message("Updated my database!", ephemeral=True)
        self.logger.info("Finished updating messages")

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message) -> None:
        if not config.Main.LOG_MESSAGES:
            return
        if not message.guild or message.clean_content == "":
            return
        if not self.data:
            self.data = self.get_data()
        self.logger.debug(f"Collecting message: member='{message.author}', id='{message.id}' content='{message.content}'")
        guild = message.guild
        guild_id = str(guild.id)
        channel = message.channel
        channel_id = str(channel.id)
        message_id = str(message.id)
        self.data[guild_id] = {
            channel_id:{
                message_id:{
                    "member_id":message.author.id,
                    "content":message.content
                    }
                }
            }
        self.set_data(self.data)

    async def get_message(self, interaction:discord.Interaction, guild:discord.Guild=None) -> None:
        if not self.data:
            self.data = self.get_data()
        guild_id = str(guild.id)
        if guild is None:
            guild = interaction.guild
        if guild_id not in self.data:
            self.data[guild_id] = {}
        for channel in guild.channels:
            if channel.type in [discord.ChannelType.category, discord.ChannelType.forum]:
                continue
            channel_id = str(channel.id)
            if channel_id not in self.data[guild_id]:
                self.data[guild_id][channel_id] = {}
            self.logger.debug(f"Getting messages from: guild='{guild}, channel='{channel}'")
            async for message in channel.history(limit=config.Message.LIMIT):
                if str(message.id) in self.data[guild_id][channel_id]:
                    break
                if message.content in ["", "[Original Message Deleted]"]:
                    # Skip empty contents (I.e. Bot embeds etc.)
                    continue
                self.data[guild_id][channel_id][str(message.id)] = {"member_id":str(message.author.id), "content":str(message.content)}
            if not self.data[guild_id][channel_id]:
                # Clean-up data if channel has no messages.
                del self.data[guild_id][channel_id]
        self.set_data(self.data)

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Messages(bot))
