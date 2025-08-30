"""Module for handling automod flag message events."""
from typing import override

from discord import Embed
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class AutomodFlagMessage(AuditEvent):
    """Handle automod flag message events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_flag_message
        self.logger.debug(f"on automod_flag_message: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target

        return Embed(
            title="Automod Flag Message",
            description=f"Automod flagged a message from {target} with reason: {self.entry.reason}",
            color=Settings.changed_color,
        )
