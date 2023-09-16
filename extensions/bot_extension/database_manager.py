import datetime

import discord  # type: ignore
from discord import InteractionType, app_commands
from discord.ext import tasks

from tools.config_reader import config
from tools.database_tables import Session, engine, Channel, Guild, Message, User, Presence
from _types.cogs import Cog
from _types.bot import WinterDragon


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class DatabaseSetup(Cog):
    async def cog_load(self) -> None:
        self.update.start()


    @Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        with Session(engine) as session:
            db_msg = session.query(Message).where(Message.id == message.id).first()
            if db_msg is not None:
                self.logger.debug(f"Deleting from Messages table, message was deleted from discord. {message=}")
                session.delete(db_msg)
            session.commit()



    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if isinstance(message.channel, discord.DMChannel):
            return

        if not message.guild:
            self.logger.warning(f"No guild found: {message=}")
            return

        self._add_db_guild(message.guild)
        self._add_db_user(message.author)
        self._add_db_channel(message.channel)
        self._add_db_message(message)


    def _add_db_message(self, message: discord.Message) -> None:
        with Session(engine) as session:
            if session.query(Message).where(Message.id == message.id).first() is None:
                self.logger.debug(f"Adding new {message=} to Messages table")
                
                session.add(Message(
                    id = message.id,
                    content = message.clean_content,
                    user_id = message.author.id,
                    channel_id = message.channel.id,
                    guild_id = message.guild.id if message.guild else None
                ))
                session.commit()


    def _add_db_channel(self, channel: discord.abc.GuildChannel) -> None:
        with Session(engine) as session:
            if session.query(Channel).where(Channel.id == channel.id).first() is None:
                self.logger.info(f"Adding new {channel=} to Channels table")
                session.add(Channel(
                    id = channel.id,
                    name = f"{channel.name}",
                    type = None,
                    guild_id = channel.guild.id,
                ))
                session.commit()


    def _add_db_user(self, user: discord.Member) -> None:
        with Session(engine) as session:
            if session.query(User).where(User.id == user.id).first() is None:
                self.logger.debug(f"Adding new {user=} to User table")
                session.add(User(id = user.id))
                session.commit()


    def _add_db_guild(self, guild: discord.Guild) -> None:
        with Session(engine) as session:
            if session.query(Guild).where(Guild.id == guild.id).first() is None:
                self.logger.info(f"Adding new {guild=} to Guild table")
                session.add(Guild(id = guild.id))
                session.commit()


    @tasks.loop(hours=1)
    async def update(self) -> None:
        for user in self.bot.users:
            self._add_db_user(user)
        for guild in self.bot.guilds:
            self._add_db_guild(guild)

    @update.before_loop # type: ignore
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    async def remove_old_presences(self, member: discord.Member) -> None:
        with Session(engine) as session:
            db_presences = session.query(Presence).where(Presence.user_id == member.id).all()
            for presence in db_presences:
                if (presence.date_time + datetime.timedelta(days=365)) >= datetime.datetime.now(datetime.timezone.utc):
                    self.logger.debug(f"Removing year old presence {presence.id=}")
                    session.delete(presence)
                else:
                    self.logger.debug(f"Presence data not older then a year {presence.id=}")
            session.commit()


    @Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        member = after or before
        date_time = datetime.datetime.now()
        ten_sec_ago = date_time - datetime.timedelta(seconds=10)
        self.logger.debug(f"presence update for {member}, at {date_time}")
        with Session(engine) as session:
            # Every guild a member is in calls this event.
            # Filter out updates from <10 seconds ago
            if (
                presences := session.query(Presence).where(
                    Presence.user_id == member.id,
                    Presence.date_time >= ten_sec_ago
                ).all()
            ):
                for presence in presences:
                    self.logger.debug(f"{member.status.name == presence.status=}")
                    if member.status.name == presence.status:
                        return

            self.logger.debug(f"adding presence update to database for {member}")
            session.add(Presence(
                user_id = member.id,
                status = member.status.name,
                date_time = date_time
            ))
            session.commit()


    @Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        self.logger.debug(f"on interaction: {interaction=}")
        if interaction.type not in [
            InteractionType.ping,
            InteractionType.application_command
        ]:
            return
        
        self._add_db_user(interaction.user)

        user = interaction.user
        command = interaction.command
        channel = interaction.channel
        extras = interaction.extras
        # Track command used data in database
        # https://discordpy.readthedocs.io/en/latest/api.html#discord.on_interaction




async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(DatabaseSetup(bot))  # type: ignore
