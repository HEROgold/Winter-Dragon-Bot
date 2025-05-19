"""."""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CREATED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class ScheduledEventCreate(AuditEvent):
    """Handle scheduled event create events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.scheduled_event_create
        self.logger.debug(f"on scheduled_event_create: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        event = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        event_name = getattr(event, "name", str(event))

        return Embed(
            title="Scheduled Event Created",
            description=f"{user.mention} created scheduled event `{event_name}` with reason: {self.entry.reason}",
            color=CREATED_COLOR,
        )

