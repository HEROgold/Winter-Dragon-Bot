"""."""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CREATED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class BotAdd(AuditEvent):
    """Handle bot add events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.bot_add
        self.logger.debug(f"on bot_add: {self.entry.guild=}, {self.entry=}")

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
            title="Bot Add",
            description=f"{user.mention} added {target.mention} with reason: {self.entry.reason}",
            color=CREATED_COLOR,
        )

