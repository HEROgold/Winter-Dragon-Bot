"""Module to help remembering user roles when they leave and rejoin the server."""

import discord
from discord import app_commands
from sqlmodel import select

from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.bot.core.config import Config
from winter_dragon.database.tables import AutoReAssign as AutoReAssignDb
from winter_dragon.database.tables import UserRoles
from winter_dragon.database.tables.associations.guild_roles import GuildRoles
from winter_dragon.database.tables.role import Roles


class AutoReAssign(GroupCog, auto_load=True):
    """Cog to help re-assigning user roles when they leave and rejoin the server."""

    auto_reassign_reason = Config("Member joined again, AutoAssigned roles the user had previously")

    @Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """When a member is kicked or banned, remember their roles for auto-assignment later."""
        async for entry in member.guild.audit_logs(limit=1):
            self.remember_roles(member, entry)

    def remember_roles(self, member: discord.Member, entry: discord.AuditLogEntry) -> None:
        """When a member is kicked or banned, remember their roles for auto-assignment later."""
        if entry.action in [
            discord.AuditLogAction.ban,
            discord.AuditLogAction.kick,
        ]:
            for role in member.roles:
                user_role = UserRoles(role_id=role.id, user_id=member.id)
                guild_role = GuildRoles(guild_id=member.guild.id, role_id=role.id)
                self.session.add(user_role)
                self.session.add(guild_role)
            self.session.commit()

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """When a member joins, check if they have any roles to be auto-assigned."""
        guild = member.guild
        for role in self.session.exec(select(Roles).join(UserRoles).join(GuildRoles).where(
            UserRoles.user_id == member.id,
            GuildRoles.guild_id == guild.id,
        )).all():
            if role.id is None:
                self.logger.critical(f"on_member_join: Role ID is none for role {role=}, {guild=}")
                continue
            if role := guild.get_role(role.id):
                await member.add_roles(role, reason=self.auto_reassign_reason)
                self.logger.debug(
                    f"Added AutoAssign remembered role {role} to new member {member.mention} in {guild}",
                )

    @app_commands.command(name="enable", description="Enable the AutoReAssign feature")
    async def slash_enable(self, interaction: discord.Interaction) -> None:
        """Enable the AutoReAssign feature for the guild."""
        self.session.add(AutoReAssignDb(guild_id=interaction.guild.id)) # type: ignore[reportOptionalMemberAccess]
        self.session.commit()

    @app_commands.command(name="disable", description="Disable the AutoReAssign feature")
    async def slash_disable(self, interaction: discord.Interaction) -> None:
        """Disable the AutoReAssign feature for the guild."""
        self.session.delete(
            self.session.exec(
                select(AutoReAssignDb)
                .where(AutoReAssignDb.guild_id == interaction.guild.id), # type: ignore[reportOptionalMemberAccess]
            ).first(),
        )
        self.session.commit()
