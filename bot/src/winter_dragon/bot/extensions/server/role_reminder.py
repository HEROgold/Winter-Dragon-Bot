"""Module to help remembering user roles when they leave and rejoin the server."""

import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.database.tables import AutoReAssign as AutoReAssignDb
from winter_dragon.database.tables import UserRoles


AUTO_ASSIGN_REASON = "Member joined again, AutoAssigned roles the user had previously"


class AutoReAssign(GroupCog):
    """Cog to help re-assigning user roles when they leave and rejoin the server."""

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
                self.session.add(UserRoles(role_id=role.id, guild_id=member.guild.id, user_id=member.id))
            self.session.commit()

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """When a member joins, check if they have any roles to be auto-assigned."""
        for auto_assign in self.session.exec(select(UserRoles).where(
            UserRoles.user_id == member.id,
            UserRoles.guild_id == member.guild.id,
        )).all():
            if role := member.guild.get_role(auto_assign.role_id):
                await member.add_roles(role, reason=AUTO_ASSIGN_REASON)
                self.logger.debug(
                    f"Added AutoAssign remembered role {role} to new member {member.mention} in {member.guild}",
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

async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(AutoReAssign(bot))
