"""The /autoreassign command group: a member who leaves and rejoins a guild gets their roles back.

GUILD_MEMBER_REMOVE names only the user, so the roles come from the member the client's cache held until then;
a member the cache never saw (in a large guild, before they spoke or changed) leaves nothing to remember. A
database-backed member cache that would close that gap is HEROgold/Winter-Dragon-Bot#210.

Only the roles the bot may give come back (below its highest role, not managed, not deleted meanwhile), in one
request that keeps whatever roles the member got on joining, e.g. from a verification bot.
"""

lazy from typing import TYPE_CHECKING, ClassVar, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session
from wd_db.extension.lifecycle import DiscordKeyedModel, LifecycleModel, Ownership
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_db.extension.lifecycle import alive_by_id, create_or_restore, owned_by, soft_delete
lazy from wd_discord import Permissions, is_network_error
lazy from wd_discord.gateway import EventName
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.resources.guild import MemberParams
lazy from wd_discord.snowflake import Snowflake

lazy from winter_dragon.ui import CreatedEmbed, DeletedEmbed


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Iterable

    lazy from wd_discord import GuildCommandInteraction, Member, MemberRemove
    lazy from wd_discord.permission_solver import PermissionSolver


REASSIGN_REASON = "Member joined again; gave back the roles they had when they left"


class AutoReassignGuild(DiscordKeyedModel, table=True):
    """A guild that gives rejoining members their roles back; ``id`` is the guild's."""

    ownership: ClassVar[Ownership] = Ownership(guild="id")


class RememberedRole(LifecycleModel, table=True):
    """A role a member had when they left a guild that gives roles back."""

    # Bare IDs until wd-db has Guild, User and Role tables to reference; see HEROgold/Winter-Dragon-Bot#210 and HER-360.

    ownership: ClassVar[Ownership] = Ownership(member="user_id", guild="guild_id")
    natural_key: ClassVar[tuple[str, ...]] = ("guild_id", "user_id", "role_id")

    guild_id: int = Field(sa_type=BigInteger, index=True)
    user_id: int = Field(sa_type=BigInteger, index=True)
    role_id: int = Field(sa_type=BigInteger)


AUTO_REASSIGN_TABLES = (AutoReassignGuild, RememberedRole)


def is_enabled(session: Session, guild_id: Snowflake) -> bool:
    """Whether the guild ``guild_id`` gives rejoining members their roles back."""
    return guild_setting(session, guild_id) is not None


def guild_setting(session: Session, guild_id: Snowflake) -> AutoReassignGuild | None:
    """Return the alive row turning giving roles back on in the guild ``guild_id``, if any."""
    return alive_by_id(session, AutoReassignGuild, int(guild_id))


def remembered_roles(session: Session, guild_id: Snowflake, user_id: Snowflake | None = None) -> Generator[RememberedRole]:
    """Yield the roles remembered in the guild ``guild_id``: of the member ``user_id``, or of everyone without one."""
    yield from session.exec(owned_by(RememberedRole, guild=guild_id, member=user_id))


def forget(session: Session, guild_id: Snowflake, user_id: Snowflake | None = None) -> list[RememberedRole]:
    """Soft-delete the roles :func:`remembered_roles` yields, and return them; the caller commits."""
    remembered = list(remembered_roles(session, guild_id, user_id))
    for row in remembered:
        soft_delete(session, row)
    return remembered


def giveable(bot: PermissionSolver, role_ids: Iterable[Snowflake]) -> Generator[Snowflake]:
    """Yield the roles of ``role_ids`` the bot may give: still in the guild, not managed, and below its highest role."""
    roles = {role.id: role for role in bot.guild.roles}
    for role_id in role_ids:
        role = roles.get(role_id)
        if role is not None and bot.can_give_role(role):
            yield role_id


class AutoReassign(
    GroupCog,
    name="autoreassign",
    description="Give members who leave and rejoin the roles they had",
    default_member_permissions=Permissions.MANAGE_ROLES,
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
        guild_id = event.guild.id
        if member is None:
            return
        with Session(self.bind) as session:
            if not is_enabled(session, guild_id):
                return
            forget(session, guild_id, member.id)
            for role in member.roles:
                create_or_restore(session, RememberedRole(guild_id=int(guild_id), user_id=int(member.id), role_id=int(role.id)))
            session.commit()

    @Cog.listener(EventName.GUILD_MEMBER_ADD)
    async def on_member_add(self, member: Member) -> None:
        """Give a rejoining member the roles remembered from when they left, then forget them."""
        guild_id = member.guild_id
        with Session(self.bind) as session:
            if not is_enabled(session, guild_id):
                return
            role_ids = [Snowflake(row.role_id) for row in forget(session, guild_id, member.id)]
            session.commit()
        if not role_ids:
            return
        bot = await member.guild.own_permissions()
        if is_network_error(bot):
            # One role Discord refuses would fail a single request for all of them, so each goes out on its own.
            self.logger.warning(t"Could not tell which roles I may give in {guild_id}, trying each: {bot}")
            await self._give_one_by_one(member, role_ids)
            return
        given = list(giveable(bot, role_ids))
        if skipped := len(role_ids) - len(given):
            self.logger.info(t"Not giving {skipped} remembered role(s) back to {member.id} in {guild_id}: I may not")
        await self._give(member, given)

    async def _give_one_by_one(self, member: Member, role_ids: Iterable[Snowflake]) -> None:
        """Add each of ``role_ids`` in its own request, so Discord refuses only the ones it must."""
        for role_id in role_ids:
            added = await member.add_role(member.guild.role(role_id), reason=REASSIGN_REASON)
            if is_network_error(added):
                self.logger.warning(t"Could not give role {role_id} back to {member.id} in {member.guild_id}: {added}")

    async def _give(self, member: Member, role_ids: Iterable[Snowflake]) -> None:
        """Add ``role_ids`` to the member's roles in one request, keeping every role they have already."""
        current = list(member.model.roles)
        added = [role_id for role_id in role_ids if role_id not in current]
        if not added:
            return
        edited = await member.edit(MemberParams(roles=[*current, *added]), reason=REASSIGN_REASON)
        if is_network_error(edited):
            self.logger.warning(t"Could not give roles {added} back to {member.id} in {member.guild_id}: {edited}")

    @Cog.command(
        name="enable",
        description="Give members who leave and rejoin the roles they had",
        requires=Permissions.MANAGE_ROLES,
    )
    async def enable(self, interaction: GuildCommandInteraction) -> None:
        """Start remembering leaving members' roles in this guild; needs MANAGE_ROLES."""
        guild = interaction.guild
        with Session(self.bind) as session:
            if not is_enabled(session, guild.id):
                create_or_restore(session, AutoReassignGuild(id=int(guild.id)))
                session.commit()
        message = "Members who leave and rejoin now get their roles back; my role must be above the roles to give."
        bot = await guild.own_permissions()
        warning = None if is_network_error(bot) else self._ungiveable_warning(bot)
        description = message if warning is None else f"{message} {warning}"
        await interaction.respond(embeds=[CreatedEmbed(description=description)], ephemeral=True)

    @staticmethod
    def _ungiveable_warning(bot: PermissionSolver) -> str | None:
        """Say what keeps the bot from giving roles back in its guild, or ``None`` when nothing does."""
        if Permissions.MANAGE_ROLES not in bot.base():
            return "I don't have the Manage Roles permission, so I can't give any roles back until I get it."
        above = [f"<@&{role.id}>" for role in bot.ungiveable_roles()]
        if not above:
            return None
        return f"These roles are above my highest role, so I can't give them back: {', '.join(above)}. Move my role above them."

    @Cog.command(
        name="disable",
        description="Stop giving rejoining members their roles back",
        requires=Permissions.MANAGE_ROLES,
    )
    async def disable(self, interaction: GuildCommandInteraction) -> None:
        """Stop remembering roles in this guild, and forget those remembered; needs MANAGE_ROLES."""
        guild_id = interaction.guild_id
        with Session(self.bind) as session:
            if (setting := guild_setting(session, guild_id)) is not None:
                soft_delete(session, setting)
            forget(session, guild_id)
            session.commit()
        description = "Rejoining members no longer get their roles back."
        await interaction.respond(embeds=[DeletedEmbed(description=description)], ephemeral=True)
