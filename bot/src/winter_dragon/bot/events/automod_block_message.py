"""Module for handling automod block message events."""
from typing import override

from discord import Embed
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class AutomodBlockMessage(AuditEvent):
    """Handle automod block message events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_block_message
        self.logger.debug(f"on automod_block_message: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target

        return Embed(
            title="Automod Block Message",
            description=f"Automod blocked a message from {target} with reason: {self.entry.reason}",
            color=Settings.deleted_color,
        )
