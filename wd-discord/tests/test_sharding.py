"""Unit tests: gateway sharding helpers and ShardManager batching (no sockets)."""
from __future__ import annotations

from typing import Any

import pytest
from wd_discord.gateway import (
    GatewayBotInfo,
    SessionStartLimit,
    ShardManager,
    build_identify,
    identify_batches,
    parse_gateway_bot,
    rate_limit_key,
    shard_id_for_guild,
)
from wd_discord.gateway import sharding as sharding_module


GATEWAY_BOT_PAYLOAD = {
    "url": "wss://gateway.discord.gg",
    "shards": 9,
    "session_start_limit": {"total": 1000, "remaining": 999, "reset_after": 14400000, "max_concurrency": 1},
}


def test_shard_id_for_guild() -> None:
    guild_id = (5 << 22) | 12345  # low 22 bits must not affect routing
    assert shard_id_for_guild(guild_id, 9) == 5
    assert shard_id_for_guild(guild_id, 4) == 1
    assert shard_id_for_guild(0, 3) == 0


def test_rate_limit_key() -> None:
    assert rate_limit_key(0, 16) == 0
    assert rate_limit_key(17, 16) == 1


def test_identify_batches_chunks_in_order() -> None:
    assert identify_batches(list(range(5)), 2) == [[0, 1], [2, 3], [4]]
    assert identify_batches([3, 0, 2, 1], 4) == [[0, 1, 2, 3]]
    assert identify_batches([], 1) == []


def test_parse_gateway_bot() -> None:
    info = parse_gateway_bot(GATEWAY_BOT_PAYLOAD)
    assert info.url == "wss://gateway.discord.gg"
    assert info.shards == 9
    assert info.session_start_limit == SessionStartLimit(total=1000, remaining=999, reset_after=14400000, max_concurrency=1)
    assert info.connect_url == "wss://gateway.discord.gg?v=10&encoding=json"


def test_build_identify_includes_shard_pair() -> None:
    data = build_identify("token", 513, shard=(0, 9))
    assert data["shard"] == [0, 9]
    assert data["token"] == "token"
    assert data["intents"] == 513


def test_build_identify_omits_shard_when_not_sharding() -> None:
    assert "shard" not in build_identify("token", 0)


def _info(*, shards: int = 3, remaining: int = 100, max_concurrency: int = 1) -> GatewayBotInfo:
    return GatewayBotInfo(
        url="wss://gateway.discord.gg",
        shards=shards,
        session_start_limit=SessionStartLimit(
            total=1000,
            remaining=remaining,
            reset_after=14400000,
            max_concurrency=max_concurrency,
        ),
    )


class FakeGateway:
    """Stands in for Gateway: records construction and connect/close calls."""

    connect_order: list[int] = []
    instances: list[FakeGateway] = []

    def __init__(self, token: str, *, intents: int = 0, url: str = "", shard: tuple[int, int] | None = None) -> None:
        self.token = token
        self.intents = intents
        self.url = url
        self.shard = shard
        self.closed = False
        FakeGateway.instances.append(self)

    async def connect(self, *, presence: dict[str, Any] | None = None) -> dict[str, Any]:
        assert self.shard is not None
        FakeGateway.connect_order.append(self.shard[0])
        return {"shard": self.shard, "presence": presence}

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_gateway(monkeypatch: pytest.MonkeyPatch) -> type[FakeGateway]:
    FakeGateway.connect_order = []
    FakeGateway.instances = []
    monkeypatch.setattr(sharding_module, "Gateway", FakeGateway)
    return FakeGateway


@pytest.fixture
def recorded_sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(sharding_module.asyncio, "sleep", fake_sleep)
    return sleeps


async def test_start_batches_and_delays(fake_gateway: type[FakeGateway], recorded_sleeps: list[float]) -> None:
    manager = ShardManager("token", _info(shards=5, max_concurrency=2), intents=513)
    readies = await manager.start()

    assert len(readies) == 5
    assert fake_gateway.connect_order == [0, 1, 2, 3, 4]
    # 3 batches ([0,1], [2,3], [4]) -> a 5s wait before the 2nd and 3rd only.
    assert recorded_sleeps == [sharding_module.IDENTIFY_BATCH_DELAY] * 2
    assert [shard.shard for shard in manager.shards] == [(i, 5) for i in range(5)]
    assert all(shard.url == "wss://gateway.discord.gg?v=10&encoding=json" for shard in manager.shards)


async def test_start_respects_session_start_budget(fake_gateway: type[FakeGateway]) -> None:
    manager = ShardManager("token", _info(shards=3, remaining=2))
    with pytest.raises(RuntimeError, match="session starts"):
        await manager.start()
    assert fake_gateway.connect_order == []


@pytest.mark.usefixtures("fake_gateway")
async def test_num_shards_overrides_recommendation(recorded_sleeps: list[float]) -> None:
    manager = ShardManager("token", _info(shards=9, max_concurrency=16), num_shards=2)
    await manager.start()
    assert [shard.shard for shard in manager.shards] == [(0, 2), (1, 2)]
    assert recorded_sleeps == []  # one batch, no waits


@pytest.mark.usefixtures("fake_gateway", "recorded_sleeps")
async def test_shard_for_guild_routes_after_start() -> None:
    manager = ShardManager("token", _info(shards=3, max_concurrency=16))
    with pytest.raises(RuntimeError, match="not started"):
        manager.shard_for_guild(1 << 22)
    await manager.start()
    assert manager.shard_for_guild((4 << 22) | 7).shard == (1, 3)


async def test_close_closes_all_shards(fake_gateway: type[FakeGateway], recorded_sleeps: list[float]) -> None:  # noqa: ARG001
    manager = ShardManager("token", _info(shards=2, max_concurrency=16))
    await manager.start()
    await manager.close()
    assert len(fake_gateway.instances) == 2
    assert all(shard.closed for shard in fake_gateway.instances)
    assert manager.shards == []
