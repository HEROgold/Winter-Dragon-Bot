"""."""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class Ban(AuditEvent):
    """Handle ban events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.ban
        self.logger.debug(f"on ban: {self.entry.guild=}, {self.entry=}")
        # TODO: add to DB

    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(target, (User, Member)):
            msg = f"Target is not a discord user: {target=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Ban",
            description=f"{user.mention} banned {target.mention} {target.name} with reason: {self.entry.reason}",
            color=DELETED_COLOR,
        )

