"""Monitor and log thread update events in Discord servers.

Track when users modify existing threads and generate appropriate audit logs.
"""

from typing import override

from discord import Embed, Member, Thread, User
from winter_dragon.bot.constants import CREATED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class ThreadUpdate(AuditEvent):
    """Process thread update events in Discord guilds.

    Monitor the audit log for thread modifications, log the events,
    and create notification embeds with relevant information about changes.
    """

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.thread_update
        self.logger.debug(f"on thread_update: {self.entry.guild=}, {self.entry.target=}")


    @override
    def create_embed(self) -> Embed:  # sourcery skip: extract-duplicate-method
        thread = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(thread, Thread):
            msg = f"Thread is not a discord thread: {thread=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Thread Updated",
            description=f"{user.mention} updated {thread.type} {thread.mention} with reason: {self.entry.reason}",
            color=CREATED_COLOR,
        )

