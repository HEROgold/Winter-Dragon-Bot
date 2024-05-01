import discord

from _types.bot import WinterDragon
from _types.cogs import Cog, GroupCog
from tools.database_tables import Session, UserRoles, engine


# TODO: move this and other static messages to messages config?
AUTO_ASSIGN_REASON = "Member joined again, AutoAssign roles the user had previously"


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
            with Session(engine) as session:
                for role in member.roles:
                    session.add(UserRoles(id=role.id, user=member.id))

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        with Session(engine) as session:
            for auto_assign in session.query(UserRoles).where(
                UserRoles.user_id == member.id,
                UserRoles.guild_id == member.guild.id,
            ).all():
                role = member.guild.get_role(role_id=auto_assign.role_id) # type: ignore
                await member.add_roles(role, reason=AUTO_ASSIGN_REASON)
        self.logger.debug(f"Added AutoAssign remembered role {role} to new member {member.mention} in {member.guild}")


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(AutoReAssign(bot))
