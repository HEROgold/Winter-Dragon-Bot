"""."""
from typing import override

from discord import AuditLogAction, Embed, Member, User
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class InviteCreate(AuditEvent, action=AuditLogAction.invite_create):
    """Handle invite create events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.invite_create
        invite = self.entry.target
        self.logger.debug(f"On invite create: {self.entry.guild=}, {invite=}")


    @override
    def create_embed(self) -> Embed:
        invite = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Created Invite",
            description=f"{user.mention} created invite {invite} with reason: {self.entry.reason}",
            color=Settings.created_color,
        )
