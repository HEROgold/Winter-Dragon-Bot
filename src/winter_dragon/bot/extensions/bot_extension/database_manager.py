"""Module for tracking user, guild, role and channel data in the database."""

import datetime
from typing import override

import discord
from discord import AuditLogAction, Thread, app_commands
from herogold.log import LoggerMixin
from sqlmodel import select

from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.events.audit_event import AuditEvent
from winter_dragon.database.constants import SessionMixin
from winter_dragon.database.tables import AssociationUserCommand as AUC  # noqa: N817
from winter_dragon.database.tables import Channels, Commands, Guilds, Messages, Presence, Roles, Users


# For every existing action, create a generic event listener
# that just logs the action
for action in AuditLogAction:

    class EventListener(AuditEvent, action=action):
        """Generic audit event listener for a single audit log action."""

        @override
        async def handle(self) -> None:
            helper = _EventListenerHelper()
            helper.logger.debug(f"Registered audit event for action: {self.entry.action}")

        @override
        def create_embed(self) -> discord.Embed:
            embed = discord.Embed(
                title=f"Audit Log Event: {self.entry.action.name}",
                description=f"User: {self.entry.user} | Target: {self.entry.target} | Action: {self.entry.action.name}",
                color=discord.Color.blue(),
                timestamp=self.entry.created_at,
            )
            embed.set_footer(text=f"ID: {self.entry.id}")
            return embed


class _EventListenerHelper(SessionMixin, LoggerMixin):
    """Helper class for audit event listeners."""

    def add_db_role(self, role: discord.Role) -> None:
        if not self.session.exec(select(Roles).where(Roles.id == role.id)).first():
            self.logger.debug(f"Adding new {role=} to Roles table")
            self.session.add(Roles(id=role.id, name=role.name))
            self.session.commit()

    def add_db_message(self, message: discord.Message) -> None:
        if self.session.exec(select(Messages).where(Messages.id == message.id)).first() is None:
            self.logger.debug(f"Adding new {message=} to Messages table")

            self.session.add(
                Messages(
                    id=message.id,
                    content=message.clean_content,
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                ),
            )
            self.session.commit()

    def add_db_channel(self, channel: discord.abc.GuildChannel | Thread) -> None:
        if self.session.exec(select(Channels).where(Channels.id == channel.id)).first() is None:
            self.logger.info(f"Adding new {channel=} to Channels table")
            self.session.add(
                Channels(
                    id=channel.id,
                    name=f"{channel.name}",
                    type=None,
                    guild_id=channel.guild.id,
                ),
            )
            self.session.commit()

    def add_db_user(self, user: discord.Member | discord.User) -> None:
        if self.session.exec(select(Users).where(Users.id == user.id)).first() is None:
            self.logger.debug(f"Adding new {user=} to User table")
            self.session.add(Users(id=user.id))
            self.session.commit()

    def add_db_guild(self, guild: discord.Guild) -> None:
        if self.session.exec(select(Guilds).where(Guilds.id == guild.id)).first() is None:
            self.logger.info(f"Adding new {guild=} to Guild table")
            self.session.add(Guilds(id=guild.id))
            self.session.commit()

    def fetch_db_command(self, command: app_commands.Command) -> Commands:
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

    def link_user_db_command(self, user: discord.Member | discord.User, command: Commands) -> None:
        """Link a database user to a command when used."""
        self.session.add(
            AUC(
                user_id=user.id,
                command_id=command.id,  # type: ignore[has-id]
            ),
        )
        self.session.commit()

    def delete_user_data(self, user: discord.Member) -> None:
        """Delete all data related to a user."""
        self.logger.info(f"Deleting all data related to {user} from the database.")
        self.session.delete(select(Users).where(Users.id == user.id))
        self.session.commit()


class OnGuildChannelUpdate(AuditEvent, action=AuditLogAction.channel_update):
    """Event listener for guild channel updates."""

    @override
    async def handle(self) -> None:
        """When a channel is updated, update it in the database."""
        helper = _EventListenerHelper()
        after = self.entry.target
        if not isinstance(after, discord.abc.GuildChannel):
            helper.logger.warning(f"Audit log target is not a GuildChannel: {after=}")
            return
        Channels.update(
            Channels(
                id=after.id,
                name=after.name,
                guild_id=after.guild.id,
            ),
        )

    @override
    def create_embed(self) -> discord.Embed:
        embed = super().create_embed()
        embed.title = "Guild Channel Updated"
        embed.description = f"Channel: {self.entry.target} in Guild: {self.entry.guild}"
        return embed


class OnRoleCreate(AuditEvent, action=AuditLogAction.role_create):
    """Event listener for role creation."""

    @override
    async def handle(self) -> None:
        """When a role is created, add it to the database."""
        role = self.entry.target
        helper = _EventListenerHelper()
        if not isinstance(role, discord.Role):
            helper.logger.warning(f"Audit log target is not a Role: {role=}")
            return
        helper.logger.info(f"Role created: {role} in guild {role.guild}")
        if not helper.session.exec(select(Roles).where(Roles.id == role.id)).first():
            helper.logger.debug(f"Adding new {role=} to Roles table")
            helper.session.add(Roles(id=role.id, name=role.name))
            helper.session.commit()


class OnRoleDelete(AuditEvent, action=AuditLogAction.role_delete):
    """Event listener for role deletion."""

    @override
    async def handle(self) -> None:
        """When a role is deleted, remove it from the database."""
        role = self.entry.target
        helper = _EventListenerHelper()
        if not isinstance(role, discord.Role):
            helper.logger.warning(f"Audit log target is not a Role: {role=}")
            return
        helper.logger.info(f"Role deleted: {role} in guild {role.guild}")
        if db_role := helper.session.exec(select(Roles).where(Roles.id == role.id)).first():
            helper.logger.debug(f"Deleting from Roles table, role was deleted from discord. {role=}")
            helper.session.delete(db_role)
            helper.session.commit()


class OnMessageDelete(AuditEvent, action=AuditLogAction.message_delete):
    """Event listener for message deletion."""

    @override
    async def handle(self) -> None:
        """When a message is deleted, remove it from the database."""
        message = self.entry.target
        helper = _EventListenerHelper()
        if not isinstance(message, discord.Message):
            helper.logger.warning(f"Audit log target is not a Message: {message=}")
            return
        helper.logger.info(f"Message deleted: {message.id} in channel {message.channel} of guild {message.guild}")
        db_msg = helper.session.exec(select(Messages).where(Messages.id == message.id)).first()
        if db_msg is not None:
            helper.logger.debug(f"Deleting from Messages table, message was deleted from discord. {message=}")
            helper.session.delete(db_msg)
        helper.session.commit()


class OnGuildRoleCreate(AuditEvent, action=AuditLogAction.role_create):
    """Event listener for guild role creation."""

    @override
    async def handle(self) -> None:
        """When a role is created, add it to the database."""
        role = self.entry.target
        helper = _EventListenerHelper()
        if not isinstance(role, discord.Role):
            helper.logger.warning(f"Audit log target is not a Role: {role=}")
            return
        helper.logger.info(f"Guild role created: {role} in guild {role.guild}")
        if not helper.session.exec(select(Roles).where(Roles.id == role.id)).first():
            helper.logger.debug(f"Adding new {role=} to Roles table")
            helper.session.add(Roles(id=role.id, name=role.name))
            helper.session.commit()


class OnGuildRoleDelete(AuditEvent, action=AuditLogAction.role_delete):
    """Event listener for guild role deletion."""

    @override
    async def handle(self) -> None:
        """When a role is deleted, remove it from the database."""
        role = self.entry.target
        helper = _EventListenerHelper()
        if not isinstance(role, discord.Role):
            helper.logger.warning(f"Audit log target is not a Role: {role=}")
            return
        helper.logger.info(f"Guild role deleted: {role} in guild {role.guild}")
        if db_role := helper.session.exec(select(Roles).where(Roles.id == role.id)).first():
            helper.logger.debug(f"Deleting from Roles table, role was deleted from discord. {role=}")
            helper.session.delete(db_role)
            helper.session.commit()


class OnGuildRoleUpdate(AuditEvent, action=AuditLogAction.role_update):
    """Event listener for guild role updates."""

    @override
    async def handle(self) -> None:
        """When a role is updated, update it in the database."""
        before = self.entry.before
        helper = _EventListenerHelper()
        after = self.entry.after
        if not (isinstance(before, discord.Role) and isinstance(after, discord.Role)):
            helper.logger.warning(f"Audit log target is not a Role: {before=}, {after=}")
            return
        helper.logger.info(f"Guild role updated: {before} to {after} in guild {after.guild}")
        if db_role := helper.session.exec(select(Roles).where(Roles.id == before.id)).first():
            helper.logger.debug(f"Updating {before=} to {after=} in Roles table")
            db_role.name = after.name
            helper.session.commit()


class OnPresenceUpdate(AuditEvent, action=AuditLogAction.member_update):
    """Event listener for presence updates."""

    @override
    async def handle(self) -> None:
        """Code to run whenever a presence is updated, to keep track of a users online status.

        This only updates once every 10 seconds, and only tracks online status.
        """
        before = self.entry.before
        helper = _EventListenerHelper()
        after = self.entry.after
        if not (isinstance(before, discord.Member) and isinstance(after, discord.Member)):
            helper.logger.warning(f"Audit log target is not a Member: {before=}, {after=}")
            return
        helper.logger.info(f"Presence updated for member: {after} in guild {after.guild}")
        member = after or before
        helper.add_db_user(member)
        Presence.remove_old_presences(member.id)
        date_time = datetime.datetime.now(tz=datetime.UTC)
        ten_sec_ago = date_time - datetime.timedelta(seconds=10)
        helper.logger.debug(f"presence update for {member}, at {date_time}")
        # Every guild a member is in calls this event.
        # Filter out updates from <10 seconds ago
        if presences := helper.session.exec(
            select(Presence).where(
                Presence.user_id == member.id,
                Presence.date_time >= ten_sec_ago,
            ),
        ).all():
            for presence in presences:
                if member.status.name == presence.status:
                    return

            helper.logger.debug(f"adding presence update to database for {member}")
            helper.session.add(
                Presence(
                    user_id=member.id,
                    status=member.status.name,
                    date_time=date_time,
                ),
            )
            helper.session.commit()


class CogEvents(Cog, auto_load=True):
    """Cog to register event listeners for audit log events, that are unable to be tracked via Audit Logs."""

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """When a message is sent by any user, add it to the database."""
        helper = _EventListenerHelper()
        helper.logger.info(f"Message created: {message.id} in channel {message.channel} of guild {message.guild}")
        if isinstance(message.channel, discord.DMChannel | discord.GroupChannel | discord.PartialMessageable):
            return

        if not message.guild:
            helper.logger.warning(f"No guild found when logging message: {message=}")
            return

        helper.add_db_guild(message.guild)
        helper.add_db_channel(message.channel)
        helper.add_db_user(message.author)
        helper.add_db_message(message)

    @Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """Log interaction usage to the database.

        This adds users and command to the database,
        and links both of them for tracking stats.
        """
        helper = _EventListenerHelper()
        helper.logger.info(f"Interaction occurred: {interaction.id} by user {interaction.user}")
        helper.logger.debug(f"on interaction: {interaction=}")

        user = interaction.user
        command = interaction.command
        if command is None:
            helper.logger.warning("interaction's Command is None, cannot add command to database.")
            return

        helper.add_db_user(user)
        db_cmd = helper.fetch_db_command(command)  # type: ignore  # noqa: PGH003
        helper.link_user_db_command(user, db_cmd)
