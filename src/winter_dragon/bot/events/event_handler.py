"""Module for the audit event handler."""

import discord
from discord import AuditLogAction
from herogold.log import LoggerMixin
from sqlmodel import Session, col, select

from winter_dragon.database.channel_types import Tags
from winter_dragon.database.tables.associations.channel_audit import ChannelAudit
from winter_dragon.database.tables.associations.channel_tags import ChannelTag
from winter_dragon.database.tables.channel import Channels

from .audit_event import AuditEvent


class AuditEventHandler(LoggerMixin):
    """Class for handling audit events."""

    def __init__(self, event: AuditEvent, session: Session) -> None:
        """Initialize the audit event handler."""
        self.event = event
        self.session = session

    async def handle(self) -> None:
        """Handle the audit event."""
        await self.event.handle()
        if Channels.get_by_tag(self.session, Tags.LOGS, self.event.entry.guild.id):
            await self.send_logs(
                audit_action=self.event.entry.action,
                guild=self.event.entry.guild,
                embed=self.event.create_embed(),
            )

    async def send_logs(
        self,
        audit_action: AuditLogAction,
        guild: discord.Guild,
        embed: discord.Embed,
    ) -> None:
        """Send logs to the appropriate channel."""
        channels = self.session.exec(
            select(Channels)
            .join(ChannelTag, col(ChannelTag.channel_id) == col(Channels.id))
            .join(ChannelAudit, col(ChannelAudit.channel_id) == col(Channels.id))
            .where(
                Channels.guild_id == guild.id,
                ChannelTag.tag == Tags.LOGS,
                ChannelAudit.audit_action == audit_action.value,
            )
        ).all()

        if not channels:
            self.logger.debug(f"Found no logs channel: {audit_action.name=}, {guild=}, {embed=}")
            return

        for channel in channels:
            if log_channel := discord.utils.get(guild.text_channels, id=channel.id):
                await log_channel.send(embed=embed)
                self.logger.debug(f"Send logs to {audit_action.name}'s channel: {log_channel=}")
