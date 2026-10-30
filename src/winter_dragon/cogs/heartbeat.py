"""A cog demonstrating independent background work, not just reacting to dispatch events."""

lazy from wd_bot.cogs import Cog

lazy from winter_dragon.config import CogConfig


class HeartbeatSettings:
    """Settings for the heartbeat, in its ``cogs.ini`` section."""

    interval = CogConfig(60)
    """Seconds between two heartbeat log lines."""


class Heartbeat(Cog):
    """Logs "still alive" every :attr:`HeartbeatSettings.interval` seconds for as long as the cog is loaded."""

    @Cog.periodic(seconds=lambda: HeartbeatSettings.interval)
    async def beat(self) -> None:
        """Log a heartbeat; the bot repeats it at the configured interval and stops when the cog unloads."""
        self.logger.debug(t"Heartbeat: still alive")
