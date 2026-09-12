"""A cog that logs real gateway dispatch events at DEBUG level.

Same event pair as wd-bot/tests/fixtures/example_cog.py (MESSAGE_CREATE/GUILD_CREATE), but
logging instead of accumulating results in memory - appropriate for a long-running process
whose output is meant to be read from the log file afterward, not inspected in-process.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_bot.cogs import Cog
lazy from wd_discord.gateway import EventName


if TYPE_CHECKING:
    lazy from wd_discord.gateway import GuildCreate, Message


class MessageLogger(Cog):
    """Logs every MESSAGE_CREATE/GUILD_CREATE it's dispatched, at DEBUG level."""

    @Cog.listener(EventName.MESSAGE_CREATE)
    async def on_message_create(self, message: Message) -> None:
        """Log a dispatched MESSAGE_CREATE event."""
        self.logger.debug(t"MESSAGE_CREATE: {message.author.username}: {message.content!r}")

    @Cog.listener(EventName.GUILD_CREATE)
    async def on_guild_create(self, guild: GuildCreate) -> None:
        """Log a dispatched GUILD_CREATE event."""
        self.logger.debug(t"GUILD_CREATE: {guild.name!r} (id {guild.id})")
