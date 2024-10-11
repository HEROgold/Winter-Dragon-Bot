import discord
from discord import app_commands

from bot import WinterDragon
from bot._types.cogs import Cog, GroupCog
from database.tables import AutoReAssign as AutoReAssignDb
from database.tables import UserRoles


AUTO_ASSIGN_REASON = "Member joined again, AutoAssigned roles the user had previously"


class AutoReAssign(GroupCog):
    @Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        async for entry in member.guild.audit_logs(limit=1):
            self.remember_roles(member, entry)

    def remember_roles(self, member: discord.Member, entry: discord.AuditLogEntry) -> None:
        if entry.action in [
            discord.AuditLogAction.ban,
            discord.AuditLogAction.kick,
        ]:
            with self.session as session:
                for role in member.roles:
                    session.add(UserRoles(role_id=role.id, guild_id=member.guild.id, user_id=member.id))
                session.commit()

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        with self.session as session:
            for auto_assign in session.query(UserRoles).where(
                UserRoles.user_id == member.id,
                UserRoles.guild_id == member.guild.id,
            ).all():
                role = member.guild.get_role(role_id=auto_assign.role_id)
                await member.add_roles(role, reason=AUTO_ASSIGN_REASON)
                self.logger.debug(f"Added AutoAssign remembered role {role} to new member {member.mention} in {member.guild}")

    @app_commands.command(name="enable", description="Enable the AutoReAssign feature")
    async def slash_enable(self, interaction: discord.Interaction) -> None:
        with self.session as session:
            session.add(AutoReAssignDb(guild_id=interaction.guild.id))
            session.commit()

    @app_commands.command(name="disable", description="Disable the AutoReAssign feature")
    async def slash_disable(self, interaction: discord.Interaction) -> None:
        with self.session as session:
            session.query(AutoReAssignDb).where(AutoReAssignDb.guild_id == interaction.guild.id).delete()
            session.commit()

async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(AutoReAssign(bot))
