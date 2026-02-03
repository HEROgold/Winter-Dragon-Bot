"""Log aggregation and pagination system for persistent log viewing.

This module manages aggregating audit log embeds into a single persistent message
on the global log channel, allowing users to paginate through logs without needing
individual channels for each action type.

The aggregator maintains an in-memory cache of recent logs and provides pagination
through the EmbedPageSource interface used by the Paginator view.
"""

from collections import deque
from datetime import UTC, datetime
from typing import NamedTuple

import discord
from herogold.log import LoggerMixin

from winter_dragon.bot.ui.paginator import EmbedPageSource


class LogEntry(NamedTuple):
    """A single log entry containing an audit event embed."""

    embed: discord.Embed
    timestamp: datetime
    action: str


class LogAggregator(LoggerMixin):
    """Manages aggregation of audit logs with pagination support.

    Maintains a cache of recent logs and provides methods for:
    - Adding new log entries
    - Updating the global log message with paginated views
    - Cleaning up old entries based on cache size limits
    """

    DEFAULT_MAX_LOGS = 100

    def __init__(self, max_logs: int = DEFAULT_MAX_LOGS) -> None:
        """Initialize the log aggregator."""
        self.max_logs = max_logs
        self.logs: deque[LogEntry] = deque(maxlen=max_logs)
        self.log_message: discord.Message | None = None

    def add_log(self, embed: discord.Embed, action: str) -> None:
        """Add a log entry to the aggregator."""
        entry = LogEntry(
            embed=embed,
            timestamp=datetime.now(UTC),
            action=action,
        )
        self.logs.append(entry)
        self.logger.debug(f"Added log entry: {action} (total: {len(self.logs)})")

    async def create_page_source(self) -> EmbedPageSource:
        """Create a page source for pagination from current logs."""
        if not self.logs:
            empty_embed = discord.Embed(
                title="No logs yet",
                description="Waiting for audit events...",
                color=discord.Color.greyple(),
                timestamp=datetime.now(UTC),
            )
            return EmbedPageSource([empty_embed])

        # Create embeds for each log entry with enhanced footer information
        embeds = []
        for i, log_entry in enumerate(reversed(self.logs), 1):
            embed = log_entry.embed.copy()
            # Ensure footer contains position and action info
            footer_text = f"Log #{len(self.logs) - i + 1} • {log_entry.action}"
            if embed.footer.text:
                footer_text = f"{embed.footer.text} • {footer_text}"
            embed.set_footer(text=footer_text)
            embeds.append(embed)

        return EmbedPageSource(embeds)

    async def update_global_log_message(
        self,
        channel: discord.TextChannel,
        paginator_view: discord.ui.View,
    ) -> discord.Message:
        """Update or create the global log message in the specified channel."""
        page_source = await self.create_page_source()
        self.logger.debug(f"Updating global log message with {len(self.logs)} entries")

        # If we already have a message, try to edit it
        if self.log_message:
            try:
                # Get the current page data
                page_data = await page_source.get_page(0)
                content, embed = await page_source.format_page(page_data, 0)

                self.log_message = await self.log_message.edit(
                    content=content or "\u200b",
                    embed=embed,
                    view=paginator_view,
                )
            except discord.NotFound:
                self.logger.debug("Previous log message not found, creating new one")
                self.log_message = None
            except discord.Forbidden:
                self.logger.warning("No permission to edit global log message")
                self.log_message = None
            else:
                self.logger.debug("Updated existing global log message")
                return self.log_message

        # Create a new message if we don't have one or couldn't edit it
        page_data = await page_source.get_page(0)
        content, embed = await page_source.format_page(page_data, 0)

        self.log_message = await channel.send(
            content or "\u200b",
            embed=embed,
            view=paginator_view,
        )
        self.logger.debug("Created new global log message")
        return self.log_message

    def get_log_count(self) -> int:
        """Get the current number of logs in the aggregator."""
        return len(self.logs)

    def clear_logs(self) -> None:
        """Clear all logs from the aggregator."""
        self.logs.clear()
        self.log_message = None
        self.logger.info("Cleared all logs from aggregator")
