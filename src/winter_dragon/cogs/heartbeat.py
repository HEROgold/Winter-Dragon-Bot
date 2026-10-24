"""A cog demonstrating independent background work, not just reacting to dispatch events."""

lazy import asyncio

lazy from wd_bot.cogs import Cog

lazy from winter_dragon.config import CogConfig


class HeartbeatSettings:
    """Settings for the heartbeat, in its ``cogs.ini`` section."""

    interval = CogConfig(60)
    """Seconds between two heartbeat log lines."""


class Heartbeat(Cog):
    """Logs "still alive" every :attr:`HeartbeatSettings.interval` seconds for as long as the bot keeps running."""

    async def load(self) -> None:
        """Start the heartbeat background task once registered with the bot."""
        self.bot.loop.create_task(self._beat())

    async def _beat(self) -> None:
        """Log a heartbeat forever, at the configured interval."""
        while True:
            await asyncio.sleep(HeartbeatSettings.interval)
            self.logger.debug(t"Heartbeat: still alive")
