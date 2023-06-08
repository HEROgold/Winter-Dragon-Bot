import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from tools.database_tables import Channel, Message, Session, User, engine


# TODO: create commands: message ranks, message query
# message query should try and count all the times a user said the query
# message ranks should count the top 10 most said words
# TODO: Add statistics (graphs?) to show to players for message ranks

# TODO: Consider removing or fixing

class Messages(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")


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
    async def slash_mass_get__message(self, interaction: discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer()
        for guild in self.bot.guilds:
            await self.get_message(interaction, guild)
        await interaction.followup.send("Updated my database!", ephemeral=True)
        self.logger.info("Finished updating messages")


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not config.Main.LOG_MESSAGES:
            return
        if not message.guild or message.clean_content == "":
            return
        self.logger.debug(f"Collecting message: member='{message.author}', id='{message.id}' content='{message.content}'")
        with Session(engine) as session:
            if session.query(User).where(User.id == message.author.id).first() is None:
                session.add(User(
                    id = message.author.id
                ))
            if session.query(Channel).where(Channel.id == message.channel.id).first() is None:
                session.add(Channel(
                    id = message.channel.id,
                    name = message.channel.name,
                    type = "normal",
                    guild_id = message.guild.id
                ))
            session.add(Message(
                id = message.id,
                content = message.content,
                user_id = message.author.id,
                channel_id = message.channel.id,
                guild_id = message.guild.id
                # channel = 
            ))
            session.commit()
        await self.bot.process_commands(message)


    async def get_message(
        self,
        interaction: discord.Interaction,
        guild: discord.Guild = None
    ) -> None:
        
        if guild is None:
            guild = interaction.guild

        self.logger.debug(f"updating {Message} for {guild}")

        # add message into db
        with Session(engine) as session:
            for channel in guild.channels:
                if channel.type in [discord.ChannelType.category, discord.ChannelType.forum]:
                    continue

                self.logger.debug(f"Getting messages from: guild='{guild}, channel='{channel}'")

                async for message in channel.history(limit=config.Message.LIMIT):
                    if message.content in ["", "[Original Message Deleted]"]:
                        # Skip empty contents (I.e. Bot embeds etc.)
                        continue
                    if session.query(Message).get(message.id) is not None:
                        continue

                    session.add(Message(
                        id = message.id,
                        content = message.content,
                        user_id = message.author.id,
                        channel_id = message.channel.id,
                        guild_id = message.guild.id
                        # channel = 
                    ))
            session.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Messages(bot))
