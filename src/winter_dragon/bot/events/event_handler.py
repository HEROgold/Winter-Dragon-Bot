"""Module for the audit event handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from herogold.log import LoggerMixin


if TYPE_CHECKING:
    import discord
    from discord import AuditLogAction
    from discord.ext.commands.bot import BotBase
    from sqlmodel import Session

    from winter_dragon.bot.extensions.server.log_channels import LogChannels

    from .audit_event import AuditEvent


class AuditEventHandler(LoggerMixin):
    """Class for handling audit events."""

    def __init__(self, event: AuditEvent, session: Session, bot: BotBase) -> None:
        """Initialize the audit event handler."""
        self.event = event
        self.session = session
        self.bot = bot

    async def handle(self) -> None:
        """Handle the audit event."""
        await self.event.handle()
        if self.bot and self.event.entry.guild.id:
            await self.dispatch_to_logs(
                audit_action=self.event.entry.action,
                guild=self.event.entry.guild,
                embed=self.event.create_embed(),
            )

    async def dispatch_to_logs(
        self,
        audit_action: AuditLogAction,
        guild: discord.Guild,
        embed: discord.Embed,
    ) -> None:
        """Dispatch a log to the appropriate channels/aggregators.

        This method now routes all logs to the aggregated log system
        via the LogChannels cog.
        """
        from winter_dragon.database.channel_types import Tags  # noqa: PLC0415
        from winter_dragon.database.tables import Channels  # noqa: PLC0415

        try:
            if not Channels.get_by_tag(self.session, Tags.LOGS, guild.id):
                self.logger.debug(f"No log channels configured for guild {guild.id}")
                return

            # Get the LogChannels cog and dispatch through aggregation
            log_channels_cog: LogChannels = self.bot.get_cog("LogChannels")  # pyright: ignore[reportAssignmentType]  # ty:ignore[invalid-assignment]
            if log_channels_cog:
                await log_channels_cog.dispatch_aggregated_log(
                    guild=guild,
                    embed=embed,
                    action=audit_action.name,
                )
                self.logger.debug(f"Dispatched aggregated log: {audit_action.name}")
            else:
                self.logger.warning("LogChannels cog not found")
        except Exception:
            self.logger.exception("Error dispatching aggregated log")
            # Rollback the session to clear the failed transaction state
            self.session.rollback()
