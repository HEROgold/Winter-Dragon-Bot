"""."""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class RoleDelete(AuditEvent):
    """Handle role delete events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.role_delete
        self.logger.debug(f"on role_delete: {self.entry.guild=}, {self.entry.target=}")


    @override
    def create_embed(self) -> Embed:
        role = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        role_name = getattr(role, "name", str(role))

        return Embed(
            title="Role Deleted",
            description=f"{user.mention} deleted role `{role_name}` with reason: {self.entry.reason}",
            color=DELETED_COLOR,
        )

