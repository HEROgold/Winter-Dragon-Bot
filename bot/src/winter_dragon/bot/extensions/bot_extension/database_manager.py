"""Module for tracking user, guild, role and channel data in the database."""

import datetime

import discord
from discord import InteractionType, app_commands
from sqlmodel import select
from winter_dragon.bot._types.aliases import GChannel
from winter_dragon.bot.config import Config
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.enums.channels import ChannelTypes
from winter_dragon.bot.settings import Settings
from winter_dragon.database.tables import AssociationUserCommand as AUC  # noqa: N817
from winter_dragon.database.tables import Channels, Commands, Guilds, Messages, Presence, Roles, Users


@app_commands.guilds(Settings.support_guild_id)
class DatabaseManager(Cog):
    """Track user, guild, role and channel data in the database."""

    database_update_interval = Config(3600, float)  # 1 hour in seconds

    async def cog_load(self) -> None:
        """Load the cog."""
        await super().cog_load()
        # Configure loop interval from config
        self.update.change_interval(hours=self.database_update_interval / 3600)
        self.update.start()

    @Cog.listener()
    async def on_guild_channel_update(self, _: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
        """When a channel is updated, update it in the database."""
        Channels.update(Channels(
            id = after.id,
            name = after.name,
            type = ChannelTypes.UNKNOWN,
            guild_id = after.guild.id,
        ))

    @Cog.listener()
    async def on_role_create(self, role: discord.Role) -> None:
        """When a role is created, add it to the database."""
        self._add_db_role(role)

    def _add_db_role(self, role: discord.Role) -> None:
        if not self.session.exec(select(Roles).where(Roles.id == role.id)).first():
            self.logger.debug(f"Adding new {role=} to Roles table")
            self.session.add(Roles(id=role.id, name=role.name))
            self.session.commit()

    @Cog.listener()
    async def on_role_delete(self, role: discord.Role) -> None:
        """When a role is deleted, remove it from the database."""
        if db_role := self.session.exec(select(Roles).where(Roles.id == role.id)).first():
            self.logger.debug(f"Deleting from Roles table, role was deleted from discord. {role=}")
            self.session.delete(db_role)
            self.session.commit()


    @Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """When a message is deleted, remove it from the database."""
        db_msg = self.session.exec(select(Messages).where(Messages.id == message.id)).first()
        if db_msg is not None:
            self.logger.debug(f"Deleting from Messages table, message was deleted from discord. {message=}")
            self.session.delete(db_msg)
        self.session.commit()

    @Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        """When a role is created, add it to the database."""
        if not self.session.exec(select(Roles).where(Roles.id == role.id)).first():
            self.logger.debug(f"Adding new {role=} to Roles table")
            self.session.add(Roles(id=role.id, name=role.name))
            self.session.commit()

    @Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        """When a role is deleted, remove it from the database."""
        if db_role := self.session.exec(select(Roles).where(Roles.id == role.id)).first():
            self.logger.debug(f"Deleting from Roles table, role was deleted from discord. {role=}")
            self.session.delete(db_role)
            self.session.commit()

    @Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        """When a role is updated, update it in the database."""
        if db_role := self.session.exec(select(Roles).where(Roles.id == before.id)).first():
            self.logger.debug(f"Updating {before=} to {after=} in Roles table")
            db_role.name = after.name
            self.session.commit()

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """When a message is sent, add it to the database."""
        # sourcery skip: collection-to-bool, remove-redundant-if, remove-unreachable-code
        if isinstance(message.channel, (
            discord.DMChannel,
            discord.GroupChannel,
            discord.PartialMessageable,
        )):
            return

        if not message.guild:
            self.logger.warning(f"No guild found when logging message: {message=}")
            return

        self._add_db_guild(message.guild)
        self._add_db_user(message.author)
        self._add_db_channel(message.channel)
        self._add_db_message(message)


    def _add_db_message(self, message: discord.Message) -> None:
        if self.session.exec(select(Messages).where(Messages.id == message.id)).first() is None:
            self.logger.debug(f"Adding new {message=} to Messages table")

            self.session.add(Messages(
                id = message.id,
                content = message.clean_content,
                user_id = message.author.id,
                channel_id = message.channel.id,
            ))
            self.session.commit()


    def _add_db_channel(self, channel: GChannel) -> None:
        if self.session.exec(select(Channels).where(Channels.id == channel.id)).first() is None:
            self.logger.info(f"Adding new {channel=} to Channels table")
            self.session.add(Channels(
                id = channel.id,
                name = f"{channel.name}",
                type = None,
                guild_id = channel.guild.id,
            ))
            self.session.commit()


    def _add_db_user(self, user: discord.Member | discord.User) -> None:
        if self.session.exec(select(Users).where(Users.id == user.id)).first() is None:
            self.logger.debug(f"Adding new {user=} to User table")
            self.session.add(Users(id=user.id))
            self.session.commit()


    def _add_db_guild(self, guild: discord.Guild) -> None:
        if self.session.exec(select(Guilds).where(Guilds.id == guild.id)).first() is None:
            self.logger.info(f"Adding new {guild=} to Guild table")
            self.session.add(Guilds(id=guild.id))
            self.session.commit()


    @loop()
    async def update(self) -> None:
        """Update the database with user, guild, role and channel info."""
        for user in self.bot.users:
            self._add_db_user(user)
        for guild in self.bot.guilds:
            self._add_db_guild(guild)
            for role in guild.roles:
                self._add_db_role(role)
            for channel in guild.channels:
                self._add_db_channel(channel)

    @update.before_loop
    async def before_update(self) -> None:
        """Wait until the bot is ready before starting the update loop."""
        await self.bot.wait_until_ready()


    @Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        """Code to run whenever a presence is updated, to keep track of a users online status.

        This only updates once every 10 seconds, and only tracks online status.
        """
        member = after or before
        self._add_db_user(member)
        Presence.remove_old_presences(member.id)
        date_time = datetime.datetime.now(tz=datetime.UTC)
        ten_sec_ago = date_time - datetime.timedelta(seconds=10)
        self.logger.debug(f"presence update for {member}, at {date_time}")
        # Every guild a member is in calls this event.
        # Filter out updates from <10 seconds ago
        if (
            presences := self.session.exec(select(Presence).where(
                Presence.user_id == member.id,
                Presence.date_time >= ten_sec_ago,
            )).all()
        ):
            for presence in presences:
                if member.status.name == presence.status:
                    return

            self.logger.debug(f"adding presence update to database for {member}")
            self.session.add(Presence(
                user_id = member.id,
                status = member.status.name,
                date_time = date_time,
            ))
            self.session.commit()


    @Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """Code to run whenever a interaction happens.

        This adds users and command to the database,
        and links both of them for tracking stats.
        Only tracks
        :class:`discord.InteractionType.ping` and
        :class:`discord.InteractionType.application_command`.
        """
        self.logger.debug(f"on interaction: {interaction=}")
        if interaction.type not in [
            InteractionType.ping,
            InteractionType.application_command,
        ]:
            return

        user = interaction.user
        command = interaction.command
        if command is None:
            self.logger.warning("interaction's Command is None, cannot add command to database.")
            return

        self._add_db_user(user)
        db_cmd = self._fetch_db_command(command) # type: ignore  # noqa: PGH003
        self._link_user_db_command(user, db_cmd)

        # Track command used data in database
        # https://discordpy.readthedocs.io/en/latest/api.html#discord.on_interaction


    def _fetch_db_command(self, command: app_commands.Command) -> Commands:
        """Return a command if it can find one, otherwise it creates one  then returns it."""
        name = command.qualified_name if command else ""
        if db_command := self.session.exec(select(Commands).where(Commands.qual_name == name)).first():
            if command.parent:
                self.logger.debug(f"{command.parent=}")
            self.logger.debug(f"{command}")
            db_command.call_count += 1
        else:
            db_command = Commands(qual_name=command.qualified_name, call_count=1)
            self.session.add(db_command)
        self.session.expire_on_commit = False
        self.session.commit()
        return db_command


    def _link_user_db_command(self, user: discord.Member | discord.User, command: Commands) -> None:
        """Link a database user to a command when used."""
        self.session.add(
            AUC(
                user_id=user.id,
                command_id=command.id, # type: ignore[has-id]
            ),
        )
        self.session.commit()

    def delete_user_data(self, user: discord.Member) -> None:
        """Delete all data related to a user."""
        self.logger.info(f"Deleting all data related to {user} from the database.")
        self.session.delete(select(Users).where(Users.id == user.id))
        self.session.commit()

async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(DatabaseManager(bot=bot))
