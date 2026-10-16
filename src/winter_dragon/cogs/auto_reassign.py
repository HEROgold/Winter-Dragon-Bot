"""The /autoreassign command group: a member who leaves and rejoins a guild gets their roles back.

GUILD_MEMBER_REMOVE names only the user, so the roles come from the member the client's cache held until then;
a member the cache never saw (in a large guild, before they spoke or changed) leaves nothing to remember.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session, select
from wd_db.extension.model import SQLModel
lazy from wd_bot.checks import member_has
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_discord import Permissions, is_network_error
lazy from wd_discord.gateway import EventName
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Iterable

    lazy from wd_discord import Client, CommandInteraction, Member, MemberRemove


REASSIGN_REASON = "Member joined again; gave back the roles they had when they left"


class AutoReassignGuild(SQLModel, table=True):
    """A guild that gives rejoining members their roles back."""

    guild_id: int = Field(sa_type=BigInteger, unique=True)


class RememberedRole(SQLModel, table=True):
    """A role a member had when they left a guild that gives roles back."""

    # TODO: Should this be a reference to Guild User and Role tables?

    guild_id: int = Field(sa_type=BigInteger, index=True)
    user_id: int = Field(sa_type=BigInteger, index=True)
    role_id: int = Field(sa_type=BigInteger)


AUTO_REASSIGN_TABLES = (AutoReassignGuild, RememberedRole)


def is_enabled(session: Session, guild_id: int) -> bool:
    """Whether the guild ``guild_id`` gives rejoining members their roles back."""
    return session.exec(select(AutoReassignGuild).where(AutoReassignGuild.guild_id == guild_id)).first() is not None


def remembered_roles(session: Session, guild_id: int, user_id: int | None = None) -> Generator[RememberedRole]:
    """Yield the roles remembered in the guild ``guild_id``: of the member ``user_id``, or of everyone without one."""
    query = select(RememberedRole).where(RememberedRole.guild_id == guild_id)
    if user_id is not None:
        query = query.where(RememberedRole.user_id == user_id)
    yield from session.exec(query)


def forget(session: Session, guild_id: int, user_id: int | None = None) -> list[RememberedRole]:
    """Delete the roles :func:`remembered_roles` yields, and return them; the caller commits."""
    remembered = list(remembered_roles(session, guild_id, user_id))
    for row in remembered:
        session.delete(row)
    return remembered


def assignable(client: Client, guild_id: Snowflake, role_ids: Iterable[Snowflake]) -> Generator[Snowflake]:
    """Yield the roles of ``role_ids`` that can be given back: those the guild still has and that aren't managed.

    A managed role belongs to an integration (a bot's own role, a booster role), which Discord alone hands out.
    When the client doesn't know the guild, every role is tried, and Discord refuses the ones it must.
    """
    state = client.cache.guild(guild_id)
    for role_id in role_ids:
        role = None if state is None else state.roles.get(role_id)
        if state is None or (role is not None and not role.managed):
            yield role_id


class AutoReassign(
    GroupCog,
    name="autoreassign",
    description="Give members who leave and rejoin the roles they had",
    contexts=[InteractionContextType.GUILD],
):
    """Remembers a leaving member's roles, and gives them back when they rejoin."""

    @override
    async def load(self) -> None:
        """Create the auto-reassign tables if missing."""
        self.create_tables(*AUTO_REASSIGN_TABLES)

    @Cog.listener(EventName.GUILD_MEMBER_REMOVE)
    async def on_member_remove(self, event: MemberRemove) -> None:
        """Remember the roles of a member leaving a guild that gives roles back, replacing what was remembered."""
        member = event.member
        guild_id = int(event.guild.id)
        if member is None:
            return
        with Session(self.bind) as session:
            if not is_enabled(session, guild_id):
                return
            forget(session, guild_id, int(member.id))
            session.add_all(
                RememberedRole(guild_id=guild_id, user_id=int(member.id), role_id=int(role.id)) for role in member.roles
            )
            session.commit()

    @Cog.listener(EventName.GUILD_MEMBER_ADD)
    async def on_member_add(self, member: Member) -> None:
        """Give a rejoining member the roles remembered from when they left, then forget them."""
        guild_id = int(member.guild_id)
        with Session(self.bind) as session:
            if not is_enabled(session, guild_id):
                return
            role_ids = [Snowflake(row.role_id) for row in forget(session, guild_id, int(member.id))]
            session.commit()
        guild = member.guild
        for role_id in assignable(self.bot.client, member.guild_id, role_ids):
            added = await member.add_role(guild.role(role_id), reason=REASSIGN_REASON)
            if is_network_error(added):
                self.logger.warning(t"Could not give role {role_id} back to {member.id} in {guild_id}: {added}")

    async def _role_managers_only(self, interaction: CommandInteraction) -> bool:
        """Whether the invoker may turn giving roles back on or off; tells them otherwise."""
        if interaction.guild is not None and member_has(interaction, Permissions.MANAGE_ROLES):
            return True
        await interaction.respond("You need the Manage Roles permission for that.", ephemeral=True)
        return False

    @Cog.command(name="enable", description="Give members who leave and rejoin the roles they had")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def enable(self, interaction: CommandInteraction) -> None:
        """Start remembering leaving members' roles in this guild; needs MANAGE_ROLES."""
        guild = interaction.guild
        if guild is None or not await self._role_managers_only(interaction):
            return
        with Session(self.bind) as session:
            if not is_enabled(session, int(guild.id)):
                session.add(AutoReassignGuild(guild_id=int(guild.id)))
                session.commit()
        await interaction.respond(
            "Members who leave and rejoin now get their roles back; my role must be above the roles to give.",
            ephemeral=True,
        )

    @Cog.command(name="disable", description="Stop giving rejoining members their roles back")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def disable(self, interaction: CommandInteraction) -> None:
        """Stop remembering roles in this guild, and forget those remembered; needs MANAGE_ROLES."""
        guild = interaction.guild
        if guild is None or not await self._role_managers_only(interaction):
            return
        guild_id = int(guild.id)
        with Session(self.bind) as session:
            for row in session.exec(select(AutoReassignGuild).where(AutoReassignGuild.guild_id == guild_id)):
                session.delete(row)
            forget(session, guild_id)
            session.commit()
        await interaction.respond("Rejoining members no longer get their roles back.", ephemeral=True)
