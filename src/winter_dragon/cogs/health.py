"""Tells the container's healthcheck that the bot is connected to Discord; see :mod:`winter_dragon.health`."""

lazy import asyncio
lazy from typing import override

lazy from wd_bot.cogs import Cog

lazy from winter_dragon.health import ALIVE_FILE


TOUCH_INTERVAL = 15.0
"""Seconds between two checks of the gateway; well under :data:`~winter_dragon.health.ALIVE_MAX_AGE`."""


class Health(Cog):
    """Touches :data:`~winter_dragon.health.ALIVE_FILE` every :data:`TOUCH_INTERVAL` while every shard is alive."""

    _task: asyncio.Task[None] | None = None

    @override
    async def load(self) -> None:
        """Start touching the alive file once registered with the bot."""
        self._task = self.bot.loop.create_task(self._run())

    @override
    async def unload(self) -> None:
        """Stop the background task."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        await super().unload()

    async def _run(self) -> None:
        """Touch the alive file forever, but only while :attr:`~wd_discord.gateway.sharding.ShardManager.alive`."""
        while True:
            manager = self.bot.shard_manager
            if manager is not None and manager.alive:
                ALIVE_FILE.touch()
            await asyncio.sleep(TOUCH_INTERVAL)
