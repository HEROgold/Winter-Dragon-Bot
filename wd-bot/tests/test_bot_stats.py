"""Unit tests: the BotStats snapshot and the /botstats command (no network)."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from sqlmodel import SQLModel
from wd_bot.testing import detached_cog
from wd_discord.cache import StateCache
from wd_discord.gateway.dispatch import parse_dispatch
from wd_discord.testing import RecordingClient, guild_create_json, member_json, user_json

from winter_dragon.bot_stats import BotStats, BotStatsSnapshot, ShardStats, latest_snapshot
from winter_dragon.cogs.bot_stats import MAX_SHARD_LINES, BotStatsCommand, shard_line, shards_value


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine
    from wd_discord.gateway.sharding import ShardManager


LAUNCH = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
APPLICATION = {
    "id": "2",
    "name": "bot",
    "icon": None,
    "description": "",
    "bot_public": True,
    "bot_require_code_grant": False,
    "verify_key": "k",
    "team": None,
    "owner": user_json(username="asker"),
}


def _cache() -> StateCache:
    """Guild 7 (10 members, channel 5, thread 6, member 3) and guild 9 (4 members, no channels, members 3 and 11)."""
    cache = StateCache()
    cache.apply(parse_dispatch("GUILD_CREATE", guild_create_json(member_count=10)))
    other = guild_create_json(
        id="9",
        member_count=4,
        channels=[],
        threads=[],
        voice_states=[],
        members=[member_json(), member_json(user=user_json(id="11", username="b"))],
    )
    cache.apply(parse_dispatch("GUILD_CREATE", other))
    return cache


def _shards(*shards: tuple[bool, float | None]) -> ShardManager:
    gateways = [
        SimpleNamespace(shard=(index, len(shards)), alive=alive, latency=latency)
        for index, (alive, latency) in enumerate(shards)
    ]
    return cast("ShardManager", SimpleNamespace(shards=gateways))


def test_the_snapshot_counts_guilds_channels_and_members() -> None:
    stats = BotStats.from_cache(_cache(), None, launch_time=LAUNCH)

    assert (stats.guilds, stats.unavailable_guilds) == (2, 0)
    assert (stats.channels, stats.threads) == (1, 1)
    assert stats.members == 14
    assert stats.cached_users == 2


def test_a_guild_without_a_member_count_counts_its_cached_members() -> None:
    cache = StateCache()
    cache.apply(parse_dispatch("GUILD_CREATE", guild_create_json(member_count=None)))

    assert BotStats.from_cache(cache, None, launch_time=LAUNCH).members == 1


def test_the_snapshot_reads_every_shard() -> None:
    stats = BotStats.from_cache(StateCache(), _shards((True, 0.042), (False, None)), launch_time=LAUNCH)

    assert stats.shards == (ShardStats(id=0, alive=True, latency=0.042), ShardStats(id=1, alive=False, latency=None))
    assert stats.shards_alive == 1


def test_uptime_runs_from_launch_to_the_snapshot() -> None:
    stats = BotStats.from_cache(StateCache(), None, launch_time=LAUNCH)

    assert stats.uptime == stats.taken_at - LAUNCH


def test_the_snapshot_survives_a_json_round_trip() -> None:
    stats = BotStats.from_cache(_cache(), _shards((True, 0.042)), launch_time=LAUNCH)

    assert BotStats.model_validate_json(stats.model_dump_json()) == stats


def test_a_shard_line_shows_state_and_latency() -> None:
    assert shard_line(ShardStats(id=0, alive=True, latency=0.0421)) == "#0 up, 42 ms"
    assert shard_line(ShardStats(id=3, alive=False, latency=None)) == "#3 down, no heartbeat yet"


def test_many_shards_list_only_the_dead_ones() -> None:
    shards = [(True, 0.04)] * MAX_SHARD_LINES + [(False, None)]
    stats = BotStats.from_cache(StateCache(), _shards(*shards), launch_time=LAUNCH)

    assert shards_value(stats).splitlines() == [
        f"{MAX_SHARD_LINES}/{MAX_SHARD_LINES + 1} up",
        f"#{MAX_SHARD_LINES} down, no heartbeat yet",
    ]


def test_no_shards_reads_not_connected() -> None:
    assert shards_value(BotStats.from_cache(StateCache(), None, launch_time=LAUNCH)) == "Not connected"


async def test_botstats_answers_owners_privately(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("GET", "/applications/@me", APPLICATION)
    cog = detached_cog(BotStatsCommand, client=discord_client, shard_manager=None, launch_time=LAUNCH)

    await BotStatsCommand.botstats.invoke(cog, make_interaction("botstats"), [])

    (response,) = discord_client.interaction_responses()
    assert response["data"]["flags"] & 64
    assert response["data"]["embeds"][0]["title"] == "Bot stats"


async def test_botstats_refuses_everyone_else(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("GET", "/applications/@me", {**APPLICATION, "owner": user_json(id="99", username="o")})
    cog = detached_cog(BotStatsCommand, client=discord_client, shard_manager=None, launch_time=LAUNCH)

    await BotStatsCommand.botstats.invoke(cog, make_interaction("botstats"), [])

    assert discord_client.interaction_responses()[0]["data"]["content"] == "Only the bot's owners can do that."


async def test_the_cog_stores_a_snapshot_for_the_dashboard(engine: Engine, discord_client: RecordingClient) -> None:
    cog = detached_cog(BotStatsCommand, engine=engine, client=discord_client, shard_manager=None, launch_time=LAUNCH)
    cog.create_tables(BotStatsSnapshot)

    await cog.store()
    await cog.store()

    stored = latest_snapshot(engine)
    assert stored is not None
    assert stored.launch_time == LAUNCH


def test_there_is_no_snapshot_before_the_first(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine, tables=[BotStatsSnapshot.__table__])

    assert latest_snapshot(engine) is None
