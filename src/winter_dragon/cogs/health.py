"""Tells the container's healthcheck that the bot is connected to Discord; see :mod:`winter_dragon.health`."""

lazy from wd_bot.cogs import Cog

lazy from winter_dragon.health import ALIVE_FILE


TOUCH_INTERVAL = 15.0
"""Seconds between two checks of the gateway; well under :data:`~winter_dragon.health.ALIVE_MAX_AGE`."""


class Health(Cog):
    """Touches :data:`~winter_dragon.health.ALIVE_FILE` every :data:`TOUCH_INTERVAL` while every shard is alive."""

    @Cog.periodic(seconds=TOUCH_INTERVAL)
    async def touch_alive_file(self) -> None:
        """Touch the alive file, but only while :attr:`~wd_discord.gateway.sharding.ShardManager.alive`."""
        manager = self.bot.shard_manager
        if manager is not None and manager.alive:
            ALIVE_FILE.touch()
