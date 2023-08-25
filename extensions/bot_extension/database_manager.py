import datetime
import logging

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands, tasks
from tools import event_errors

from tools.config_reader import config
from tools.database_tables import Session, engine, Channel, Guild, Message, User, Presence


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class DatabaseSetup(commands.Cog):
    bot: commands.Bot
    logger: logging.Logger

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    async def cog_load(self) -> None:
        self.update.start()


    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        with Session(engine) as session:
            db_msg = session.query(Message).where(Message.id == message.id).first()
            if db_msg is not None:
                self.logger.debug(f"Deleting from Messages table, message was deleted from discord. {message=}")
                session.delete(db_msg)
            session.commit()



    @commands.Cog.listener()
    # @event_errors.event_logger
    async def on_message(self, message: discord.Message) -> None:
        user = message.author
        guild = message.guild
        channel = message.channel

        if isinstance(channel, discord.DMChannel):
            return

        if not guild:
            self.logger.warning(f"No guild found: {message=}")
            return

        with Session(engine) as session:
            if session.query(Guild).where(Guild.id == guild.id).first() is None:
                self.logger.info(f"Adding new {guild=} to Guild table")
                session.add(Guild(id = guild.id))

            if session.query(User).where(User.id == user.id).first() is None:
                self.logger.debug(f"Adding new {user=} to User table")
                session.add(User(id = user.id))
            session.commit()

        with Session(engine) as session:
            if session.query(Channel).where(Channel.id == channel.id).first() is None:
                self.logger.info(f"Adding new {channel=} to Channels table")
                session.add(Channel(
                    id = channel.id,
                    name = f"{channel.name}",
                    type = f"{channel.type}",
                    guild_id = guild.id,
                ))

            if session.query(Message).where(Message.id == message.id).first() is None:
                self.logger.debug(f"Adding new {message=} to Messages table")
                
                session.add(Message(
                    id = message.id,
                    content = message.clean_content,
                    user_id = user.id,
                    channel_id = channel.id,
                    guild_id = guild.id if guild else None
                ))
            session.commit()



    @tasks.loop(hours=1)
    async def update(self) -> None:
        with Session(engine) as session:
            for user in self.bot.users:
                if session.query(User).where(User.id == user.id).first() is None:
                    self.logger.info(f"Adding new {user=} to Users table")
                    session.add(User(id = user.id))
            for guild in self.bot.guilds:
                if session.query(Guild).where(Guild.id == guild.id).first() is None:
                    self.logger.info(f"Adding new {guild=} to Guild table")
                    session.add(Guild(id = guild.id))

            session.commit()

    @update.before_loop # type: ignore
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()

    async def remove_old_presences(self, member: discord.Member) -> None:
        with Session(engine) as session:
            db_presences = session.query(Presence).where(Presence.user_id == member.id).all()
            for presence in db_presences:
                if (presence.date_time + datetime.timedelta(days=1)) >= datetime.datetime.now(datetime.timezone.utc):
                    self.logger.debug(f"Removing year old presence {presence.id=}")
                    session.delete(presence)
                else:
                    self.logger.debug(f"Presence data not older then a year {presence.id=}")
            session.commit()


    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        member = before or after
        status = member.status.name
        date_time = datetime.datetime.now(datetime.timezone.utc)
        with Session(engine) as session:
            session.add(Presence(
                user_id = member.id,
                status = status,
                date_time = date_time
            ))
            session.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DatabaseSetup(bot))  # type: ignore
