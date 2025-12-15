"""."""

import logging

from discord.ext.prometheus import PrometheusCog

from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.core.settings import Settings
from winter_dragon.bot.core.tasks import loop


class Prometheus(Cog, auto_load=False):
    """Prometheus integration for the bot."""

    @loop(count=1)
    async def init(self) -> None:
        """Initialize the Prometheus cog."""
        if Settings.log_level == logging.DEBUG:
            await self.bot.add_cog(PrometheusCog(bot=self.bot))
            self.logger.info("Prometheus cog loaded. Open at localhost:8000/metrics")

    @init.before_loop
    async def before_init(self) -> None:
        """Wait until the bot is ready before starting the loops."""
        await self.bot.wait_until_ready()
