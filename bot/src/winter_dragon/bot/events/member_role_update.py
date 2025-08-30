"""."""
from typing import override

from discord import Embed, Member, Role, User
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class MemberRoleUpdate(AuditEvent):
    """Handle member role update events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.member_role_update
        self.logger.debug(f"on member_role_update: {self.entry.guild=}, {self.entry.target=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        if not isinstance(target, (User, Member)):
            self.logger.warning(f"Target is not a member: {type(target)}")
            return Embed(
                title="Member Role Update",
                description=f"{user.mention} updated roles for a member with reason: {self.entry.reason}",
                color=Settings.changed_color,
            )

        before = self.entry.before
        after = self.entry.after
        before_roles: list[Role | None] = getattr(before, "roles", [])
        after_roles: list[Role | None] = getattr(after, "roles", [])
        added_roles = [role for role in after_roles if role not in before_roles and role is not None]
        removed_roles = [role for role in before_roles if role not in after_roles and role is not None]
        description = f"{user.mention} updated roles for {target.mention} with reason: {self.entry.reason}"

        embed = Embed(
            title="Member Role Update",
            description=description,
            color=Settings.changed_color,
        )

        if added_roles:
            embed.add_field(
                name="Added Roles",
                value=", ".join(role.mention for role in added_roles),
                inline=False,
            )

        if removed_roles:
            embed.add_field(
                name="Removed Roles",
                value=", ".join(role.mention for role in removed_roles),
                inline=False,
            )

        return embed
