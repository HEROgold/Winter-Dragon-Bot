"""Unit tests: the Prometheus metrics of the bot and the dashboard (no network, no port opened)."""

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, CollectorRegistry
from wd_discord.sentry import TraceOp
from wd_discord.telemetry import REST, Timing

from winter_dragon.bot_stats import BotStats, ShardStats
from winter_dragon.metrics import BotStatsCollector, count_event, observe, observe_requests


NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
STATS = BotStats(
    taken_at=NOW,
    launch_time=NOW - timedelta(hours=2),
    version="0.9.2",
    guilds=12,
    unavailable_guilds=1,
    channels=140,
    threads=6,
    members=5321,
    cached_users=870,
    shards=(ShardStats(id=0, alive=True, latency=0.042), ShardStats(id=1, alive=False, latency=None)),
)


def _sample(name: str, labels: dict[str, str] | None = None, registry: CollectorRegistry = REGISTRY) -> float:
    return registry.get_sample_value(name, labels or {}) or 0.0


def test_the_collector_serves_the_snapshot_as_gauges() -> None:
    registry = CollectorRegistry()
    registry.register(BotStatsCollector(lambda: STATS))

    assert _sample("winter_dragon_guilds", registry=registry) == 12
    assert _sample("winter_dragon_members", registry=registry) == 5321
    assert _sample("winter_dragon_cached_users", registry=registry) == 870
    assert _sample("winter_dragon_uptime_seconds", registry=registry) == 7200
    assert _sample("winter_dragon_shard_alive", {"shard": "0"}, registry) == 1
    assert _sample("winter_dragon_shard_alive", {"shard": "1"}, registry) == 0
    assert _sample("winter_dragon_shard_latency_seconds", {"shard": "0"}, registry) == 0.042
    assert registry.get_sample_value("winter_dragon_shard_latency_seconds", {"shard": "1"}) is None


def test_the_collector_reads_a_fresh_snapshot_at_each_scrape() -> None:
    taken = iter([STATS, STATS.model_copy(update={"guilds": 13})])
    registry = CollectorRegistry()
    registry.register(BotStatsCollector(lambda: next(taken)))

    assert [_sample("winter_dragon_guilds", registry=registry) for _ in range(2)] == [12, 13]


def test_timings_land_in_their_histogram() -> None:
    work = {"kind": TraceOp.INTERACTION, "name": "/metrics-test", "outcome": "ok"}
    rest = {"route": "GET /metrics-test/{id}", "status": "200"}
    before = _sample("winter_dragon_work_seconds_count", work), _sample("winter_dragon_rest_request_seconds_count", rest)

    observe(Timing(kind=TraceOp.INTERACTION, name="/metrics-test", seconds=0.2, outcome="ok"))
    observe(Timing(kind=REST, name="GET /metrics-test/{id}", seconds=0.05, outcome="200"))

    after = _sample("winter_dragon_work_seconds_count", work), _sample("winter_dragon_rest_request_seconds_count", rest)
    assert (after[0] - before[0], after[1] - before[1]) == (1, 1)


def test_gateway_events_are_counted_by_name() -> None:
    before = _sample("winter_dragon_gateway_events_total", {"event": "METRICS_TEST"})

    count_event("METRICS_TEST")
    count_event("METRICS_TEST")

    assert _sample("winter_dragon_gateway_events_total", {"event": "METRICS_TEST"}) - before == 2


def test_dashboard_requests_are_timed_by_route_template() -> None:
    app = FastAPI()
    observe_requests(app)

    @app.get("/metrics-test/{item}")
    def item(item: str) -> dict[str, str]:
        return {"item": item}

    labels = {"method": "GET", "route": "/metrics-test/{item}", "status": "200"}
    unmatched = {"method": "GET", "route": "unmatched", "status": "404"}
    before = (
        _sample("winter_dragon_web_request_seconds_count", labels),
        _sample("winter_dragon_web_request_seconds_count", unmatched),
    )

    browser = TestClient(app)
    browser.get("/metrics-test/1")
    browser.get("/metrics-test/2")
    browser.get("/nowhere")

    after = (
        _sample("winter_dragon_web_request_seconds_count", labels),
        _sample("winter_dragon_web_request_seconds_count", unmatched),
    )
    assert (after[0] - before[0], after[1] - before[1]) == (2, 1)
