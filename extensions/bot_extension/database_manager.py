# TODO: rename file and cog to make be more logical. More descriptive of what it does.

import datetime

import discord  # type: ignore
from discord import InteractionType, app_commands
from discord.ext import tasks

from _types.bot import WinterDragon
from _types.cogs import Cog
from config import config
from tools.database_tables import AssociationUserCommand as AUC  # noqa: N817
from tools.database_tables import (
    Channel,
    Command,
    Guild,
    Message,
    Presence,
    Session,
    User,
    engine,
)


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class DatabaseManager(Cog):
    async def cog_load(self) -> None:
        self.update.start()


    @Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        with self.session as session:
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
        with self.session as session:
            if session.query(Message).where(Message.id == message.id).first() is None:
                self.logger.debug(f"Adding new {message=} to Messages table")

                session.add(Message(
                    id = message.id,
                    content = message.clean_content,
                    user_id = message.author.id,
                    channel_id = message.channel.id,
                    # guild_id = message.guild.id if message.guild else None
                ))
                session.commit()


    def _add_db_channel(self, channel: discord.abc.Messageable) -> None:
        with self.session as session:
            if session.query(Channel).where(Channel.id == channel.id).first() is None:
                self.logger.info(f"Adding new {channel=} to Channels table")
                session.add(Channel(
                    id = channel.id,
                    name = f"{channel.name}",
                    type = None,
                    guild_id = channel.guild.id,
                ))
                session.commit()


    def _add_db_user(self, user: discord.Member | discord.User) -> None:
        with self.session as session:
            if session.query(User).where(User.id == user.id).first() is None:
                self.logger.debug(f"Adding new {user=} to User table")
                session.add(User(id=user.id))
                session.commit()


    def _add_db_guild(self, guild: discord.Guild) -> None:
        with self.session as session:
            if session.query(Guild).where(Guild.id == guild.id).first() is None:
                self.logger.info(f"Adding new {guild=} to Guild table")
                session.add(Guild(id=guild.id))
                session.commit()


    @tasks.loop(hours=1)
    async def update(self) -> None:
        for user in self.bot.users:
            self._add_db_user(user)
        for guild in self.bot.guilds:
            self._add_db_guild(guild)

    @update.before_loop # type: ignore
    async def before_update(self) -> None:
        await self.bot.wait_until_ready()


    @Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        """
        Code to run whenever a presence is updated, to keep track of a users online status.
        This only updates once every 10 seconds, and only tracks online status.

        Parameters
        -----------
        :param:`before`: :class:`discord.Member`
            The Member before the update
        :param:`after`: :class:`discord.Member`
            The Member after the update
        """
        member = after or before
        Presence.remove_old_presences(member.id)
        date_time = datetime.datetime.now(tz=datetime.UTC)
        ten_sec_ago = date_time - datetime.timedelta(seconds=10)
        # self.logger.debug(f"presence update for {member}, at {date_time}")
        with self.session as session:
            # Every guild a member is in calls this event.
            # Filter out updates from <10 seconds ago
            if (
                presences := session.query(Presence).where(
                    Presence.user_id == member.id,
                    Presence.date_time >= ten_sec_ago,
                ).all()
            ):
                for presence in presences:
                    if member.status.name == presence.status:
                        return

            # self.logger.debug(f"adding presence update to database for {member}")
            session.add(Presence(
                user_id = member.id,
                status = member.status.name,
                date_time = date_time,
            ))
            session.commit()


    @Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """
        Code to run whenever a interaction happens,
        This adds users and command to the database,
        and links both of them for tracking stats.
        Only tracks
        :class:`discord.InteractionType.ping` and
        :class:`discord.InteractionType.application_command`

        Parameters
        -----------
        :param:`interaction`: :class:`discord.Interaction`
            The interaction that happened
        """
        self.logger.debug(f"on interaction: {interaction=}")
        if interaction.type not in [
            InteractionType.ping,
            InteractionType.application_command,
        ]:
            return

        user = interaction.user
        command = interaction.command

        self._add_db_user(user)
        # db_cmd = self._fetch_db_command(command)
        # self._link_db_user_command(user, db_cmd)

        channel = interaction.channel
        extras = interaction.extras
        self.logger.debug(f"{user}, {command}, {channel}, {extras}")
        # Track command used data in database
        # https://discordpy.readthedocs.io/en/latest/api.html#discord.on_interaction


    def _fetch_db_command(self, command: app_commands.Command) -> Command:
        """
        Returns a command if it can find one, otherwise it creates one
        and then returns it

        Parameters
        -----------
        :param:`command`: :class:`app_commands.Command`
            The app command to get from the database

        Returns:
        --------
            :class:`Command`: The database version of a command
        """
        with self.session as session:
            if db_command := session.query(Command).where(Command.qual_name == command.name).first():
                if command.parent:
                    self.logger.debug(f"{command.parent=}")
                self.logger.debug(f"{command}")
                db_command.call_count += 1
            else:
                db_command = Command(qual_name=command.qualified_name, call_count=1)
                session.add(db_command)
            session.expire_on_commit = False
            session.commit()
        return db_command


    def _link_db_user_command(self, user: discord.Member, command: Command) -> None:
        """
        Links a database user to a command when used

        Parameters
        -----------
        :param:`user`: :class:`discord.Member`
            The member to link a command to
        :param:`command`: :class:`Command`
            The command to link a member to
        """
        with self.session as session:
            session.add(
                AUC(
                    user_id=user.id,
                    command_id=command.id,
                ),
            )
            session.commit()


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(DatabaseManager(bot))  # type: ignore
