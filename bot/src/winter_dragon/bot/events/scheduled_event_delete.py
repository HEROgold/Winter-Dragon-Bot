from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class ScheduledEventDelete(AuditEvent):
    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.scheduled_event_delete
        self.logger.debug(f"on scheduled_event_delete: {self.entry.guild=}, {self.entry=}")


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
            title="Scheduled Event Deleted",
            description=f"{user.mention} deleted scheduled event `{event_name}` with reason: {self.entry.reason}",
            color=DELETED_COLOR,
        )

