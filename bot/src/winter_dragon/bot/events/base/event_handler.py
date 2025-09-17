"""Module for the audit event handler."""

import discord
from discord import Embed, Guild
from sqlmodel import Session, select
from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.bot.enums.channels import LogCategories
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.database.tables.channel import Channels


class AuditEventHandler(LoggerMixin):
    """Class for handling audit events."""

    def __init__(self, event: AuditEvent, session: Session) -> None:
        """Initialize the audit event handler."""
        self.event = event
        self.session = session

    async def handle(self) -> None:
        """Handle the audit event."""
        await self.event.handle()
        await self.send_channel_logs(self.event.entry.guild, self.event.create_embed(), self.event.category)

    async def send_log_to_category(
        self,
        log_category: LogCategories,
        guild: discord.Guild,
        embed: discord.Embed,
    ) -> None:
        """Send logs to the appropriate channel."""
        category_name = log_category.name

        channel = self.session.exec(select(Channels).where(
                Channels.guild_id == guild.id,
                Channels.name == category_name,
            )).first()

        if channel is None:
            self.logger.debug(f"Found no logs channel: {channel=}, {guild=}, {embed=}")
            return

        if mod_channel := discord.utils.get(guild.text_channels, id=channel.id):
            await mod_channel.send(embed=embed)

        self.logger.debug(f"Send logs to {category_name=}")

    async def send_log_to_global(
        self,
        guild: Guild,
        embed: Embed,
    ) -> None:
        """Send logs to the global log channel."""
        channel = self.session.exec(select(Channels).where(
            Channels.guild_id == guild.id,
            Channels.name == LogCategories.GLOBAL.name,
        )).first()

        if not channel:
            self.logger.warning(f"No global log channel found for {guild}")
            return
        global_log_channel = discord.utils.get(guild.text_channels, id=channel.id) or None

        self.logger.debug(f"Found: {LogCategories.GLOBAL=} as {global_log_channel=}")
        if global_log_channel is not None:
            await global_log_channel.send(embed=embed)

        self.logger.debug(f"Send logs to {global_log_channel=}")


    async def send_channel_logs(
        self,
        guild: Guild,
        embed: Embed,
        log_category: LogCategories | None=None,
    ) -> tuple[None, None]:
        """Send logs to their appropriate channel and global log channel."""
        if not guild:
            self.logger.warning("No guild found to send AuditLogEntry logs to.")
            return None, None

        self.logger.debug(f"Searching for log channels {log_category=} and {LogCategories.GLOBAL=}")

        if log_category is not None:
            await self.send_log_to_category(log_category, guild, embed)

        await self.send_log_to_global(guild, embed)
        return None, None
