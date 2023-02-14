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


# TODO: Add tracker for when user edits or deletes message > psuedocode copied from automod
#    async def on_message_edit(self, before:discord.Message, after:discord.Message):
#        self.logger.debug(f"Message edited: guild={before.guild}, channel={before.channel}, content={before.clean_content()}, changed={after.clean_content()}")
#        with contextlib.suppress(TypeError):
#            automod_channel, allmod_channel = await self.get_automod_channels("MessageEdited", before.guild)
#        try:
#            async for entry in before.guild.audit_logs(limit=1):
#                pass
#        except Exception as e:
#            self.logger.exception(e)
#
#    async def on_message_delete(self, message:discord.Message):
#        self.logger.debug(f"Message edited: guild='{message.guild}', channel='{message.channel}', content='{message.clean_content()}'")
#        try:
#            async for entry in message.guild.audit_logs(limit=1):
#                if entry.action == entry.action.message_delete:
#                    pass
#        except Exception as e:
#            self.logger.exception(e)
#

class Messages(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")
        self.data = None
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
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.data:
            self.data = await self.get_data()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    @app_commands.command(
        name = "get",
        description = f"get and store the last {config.Message.LIMIT} messages, in each channel from this server!"
        )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 300)
    async def slash_get_message(self, interaction:discord.Interaction) -> None:
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
    async def slash_mass_get__message(self, interaction:discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        for guild in self.bot.guilds:
            await self.get_message(interaction, guild)
        await interaction.followup.send("Updated my database!", ephemeral=True)
        self.logger.info("Finished updating messages")

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message) -> None:
        if not config.Main.LOG_MESSAGES:
            return
        if not message.guild or message.clean_content == "":
            return
        if not self.data:
            self.data = await self.get_data()
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
        await self.set_data(self.data)

    async def get_message(self, interaction:discord.Interaction, guild:discord.Guild=None) -> None:
        if not self.data:
            self.data = await self.get_data()
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
        await self.set_data(self.data)

async def setup(bot:commands.Bot):
    await bot.add_cog(Messages(bot))
