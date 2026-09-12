"""A cog demonstrating independent background work, not just reacting to dispatch events."""

from __future__ import annotations

lazy import asyncio

lazy from wd_bot.cogs import Cog


HEARTBEAT_INTERVAL_SECONDS = 60


class Heartbeat(Cog):
    """Logs "still alive" roughly once a minute for as long as the bot keeps running."""

    async def load(self) -> None:
        """Start the heartbeat background task once registered with the bot."""
        self.bot.loop.create_task(self._beat())

    async def _beat(self) -> None:
        """Log a heartbeat forever, at the configured interval."""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            self.logger.debug(t"Heartbeat: still alive")
