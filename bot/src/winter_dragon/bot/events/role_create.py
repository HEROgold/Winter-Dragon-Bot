"""."""
from typing import override

from discord import Embed, Member, Role, User
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class RoleCreate(AuditEvent):
    """Handle role create events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.role_create
        self.logger.debug(f"on role_create: {self.entry.guild=}, {self.entry.target=}")


    @override
    def create_embed(self) -> Embed:
        role = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        if not isinstance(role, Role):
            self.logger.warning(f"Target is not a role: {type(role)}")
            return Embed(
                title="Role Created",
                description=f"{user.mention} created a role with reason: {self.entry.reason}",
                color=Settings.created_color,
            )

        role_mention = role.mention if hasattr(role, "mention") else role.name

        return Embed(
            title="Role Created",
            description=f"{user.mention} created role {role_mention} with reason: {self.entry.reason}",
            color=Settings.created_color,
        )
