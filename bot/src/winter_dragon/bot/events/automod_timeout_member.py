"""."""
from typing import override

from discord import Embed
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class AutomodTimeoutMember(AuditEvent):
    """Handle automod timeout member events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_timeout_member
        self.logger.debug(f"on automod_timeout_member: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target

        return Embed(
            title="Automod Timeout Member",
            description=f"Automod timed out {target} with reason: {self.entry.reason}",
            color=DELETED_COLOR,
        )
