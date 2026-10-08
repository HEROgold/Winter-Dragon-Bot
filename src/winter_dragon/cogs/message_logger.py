"""A cog that logs real gateway dispatch events at DEBUG level.

Same events as wd-bot/tests/fixtures/example_cog.py (MESSAGE_CREATE/GUILD_CREATE), plus READY, but
logging instead of accumulating results in memory - appropriate for a long-running process
whose output is meant to be read from the log file afterward, not inspected in-process.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_bot.cogs import Cog
lazy from wd_discord.gateway import EventName


if TYPE_CHECKING:
    lazy from wd_discord.entities import Guild, Message, Ready


class MessageLogger(Cog):
    """Logs every READY/MESSAGE_CREATE/GUILD_CREATE it's dispatched, at DEBUG level."""

    @Cog.listener(EventName.READY)
    async def on_ready(self, ready: Ready) -> None:
        """Log a shard's READY."""
        self.logger.debug(t"READY: {ready.user.username} on shard {ready.shard}")

    @Cog.listener(EventName.MESSAGE_CREATE)
    async def on_message_create(self, message: Message) -> None:
        """Log a dispatched MESSAGE_CREATE event."""
        self.logger.debug(t"MESSAGE_CREATE: {message.author.username}: {message.content!r}")

    @Cog.listener(EventName.GUILD_CREATE)
    async def on_guild_create(self, guild: Guild) -> None:
        """Log a dispatched GUILD_CREATE event."""
        self.logger.debug(t"GUILD_CREATE: {guild.name!r} (id {guild.id})")
