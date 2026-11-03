"""The Prometheus metrics the bot and the dashboard serve on ``/metrics``, inside the compose network only.

The bot serves the :class:`~winter_dragon.bot_stats.BotStats` numbers, read at each scrape, plus how long its
interactions, listener calls, periodic ticks and REST calls take and how many gateway events arrive. These come from
:class:`~wd_discord.telemetry.Telemetry`. The dashboard serves how long each of its pages takes. Compose doesn't publish
:attr:`MetricsSettings.port`, so only the Prometheus on the same network reaches it.
"""

lazy import time
lazy from typing import TYPE_CHECKING, ClassVar, override

from prometheus_client import Counter, Histogram
from prometheus_client.registry import Collector
lazy from prometheus_client import REGISTRY, start_http_server
lazy from prometheus_client.core import GaugeMetricFamily
lazy from wd_discord.telemetry import REST, Telemetry

lazy from winter_dragon.config import Config


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator

    lazy from fastapi import FastAPI, Request
    lazy from prometheus_client import Metric
    lazy from starlette.responses import Response
    lazy from wd_discord.telemetry import Timing

    lazy from winter_dragon.bot_stats import BotStats


class MetricsSettings:
    """Where the ``/metrics`` endpoint listens, in ``config.ini``."""

    port = Config(9100)
    """The port of the ``/metrics`` endpoint, in both the bot's and the dashboard's container."""


BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
"""Histogram bucket bounds, in seconds: from a cached read to a slow command."""

WORK_SECONDS = Histogram(
    "winter_dragon_work_seconds",
    "How long an interaction, listener call or periodic tick took.",
    ["kind", "name", "outcome"],
    buckets=BUCKETS,
)
REST_SECONDS = Histogram(
    "winter_dragon_rest_request_seconds",
    "How long a Discord REST call took, rate-limit waits included.",
    ["route", "status"],
    buckets=BUCKETS,
)
GATEWAY_EVENTS = Counter("winter_dragon_gateway_events", "Gateway events received.", ["event"])
WEB_REQUEST_SECONDS = Histogram(
    "winter_dragon_web_request_seconds",
    "How long a dashboard request took.",
    ["method", "route", "status"],
    buckets=BUCKETS,
)


def observe(timing: Timing) -> None:
    """Record ``timing`` in :data:`REST_SECONDS` or :data:`WORK_SECONDS`."""
    if timing.kind == REST:
        REST_SECONDS.labels(route=timing.name, status=timing.outcome).observe(timing.seconds)
    else:
        WORK_SECONDS.labels(kind=timing.kind, name=timing.name, outcome=timing.outcome).observe(timing.seconds)


def count_event(name: str) -> None:
    """Count the gateway event ``name`` in :data:`GATEWAY_EVENTS`."""
    GATEWAY_EVENTS.labels(event=name).inc()


class BotStatsCollector(Collector):
    """Reads a fresh :class:`~winter_dragon.bot_stats.BotStats` at each scrape and serves it as gauges."""

    def __init__(self, take: Callable[[], BotStats]) -> None:
        """Serve what ``take`` returns."""
        self.take = take

    @override
    def collect(self) -> Generator[Metric]:
        """Yield the snapshot's counts, and each shard's state and latency."""
        stats = self.take()
        counts = {
            "guilds": ("Guilds the bot is in.", stats.guilds),
            "unavailable_guilds": ("Guilds down in a Discord outage.", stats.unavailable_guilds),
            "channels": ("Channels in those guilds, threads excluded.", stats.channels),
            "threads": ("Active threads the bot can see.", stats.threads),
            "members": ("The sum of each guild's member count; someone in two guilds counts twice.", stats.members),
            "cached_users": ("Distinct users among the cached members.", stats.cached_users),
            "uptime_seconds": ("Seconds since the bot started.", stats.uptime.total_seconds()),
        }
        for name, (description, value) in counts.items():
            yield GaugeMetricFamily(f"winter_dragon_{name}", description, value=value)
        alive = GaugeMetricFamily("winter_dragon_shard_alive", "1 while Discord acknowledges the shard.", labels=["shard"])
        latency = GaugeMetricFamily(
            "winter_dragon_shard_latency_seconds",
            "From the shard's last acknowledged heartbeat to the acknowledgement.",
            labels=["shard"],
        )
        for shard in stats.shards:
            alive.add_metric([str(shard.id)], int(shard.alive))
            if shard.latency is not None:
                latency.add_metric([str(shard.id)], shard.latency)
        yield alive
        yield latency


class Exporter:
    """The ``/metrics`` endpoint of this process: started once, whatever reloads the cogs do."""

    serving: ClassVar[bool] = False
    collector: ClassVar[BotStatsCollector | None] = None

    @classmethod
    def serve(cls) -> None:
        """Serve ``/metrics`` on :attr:`MetricsSettings.port`, unless this process already does."""
        if not cls.serving:
            start_http_server(MetricsSettings.port)
            cls.serving = True

    @classmethod
    def serve_bot(cls, take: Callable[[], BotStats]) -> None:
        """Serve the bot's metrics: what ``take`` returns at each scrape, and what :class:`Telemetry` reports.

        A reloaded cog calls this again with its new ``take``; the collector and subscriptions stay registered once.
        """
        if cls.collector is None:
            cls.collector = BotStatsCollector(take)
            REGISTRY.register(cls.collector)
            Telemetry.subscribe(timings=observe, events=count_event)
        else:
            cls.collector.take = take
        cls.serve()


def observe_requests(app: FastAPI) -> None:
    """Time each request ``app`` answers in :data:`WEB_REQUEST_SECONDS`, labelled by its route's path template."""

    @app.middleware("http")
    async def timed(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        path = getattr(route, "path", None) or "unmatched"
        WEB_REQUEST_SECONDS.labels(method=request.method, route=path, status=str(response.status_code)).observe(
            time.perf_counter() - start,
        )
        return response
