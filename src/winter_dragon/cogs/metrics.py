"""Serves the bot's Prometheus metrics on ``/metrics``; see :mod:`winter_dragon.metrics`."""

lazy from typing import override

lazy from wd_bot.cogs import Cog

lazy from winter_dragon.bot_stats import BotStats
lazy from winter_dragon.metrics import Exporter


class Metrics(Cog):
    """Starts the ``/metrics`` endpoint with the bot's stats, timings and gateway event counts."""

    @override
    async def load(self) -> None:
        """Serve the bot's metrics, read from this cog's bot at each scrape."""
        Exporter.serve_bot(lambda: BotStats.of(self.bot))
