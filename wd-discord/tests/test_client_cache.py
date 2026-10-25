"""Unit tests: a GET asked to be cached is reused until it expires or a write under its resource drops it."""

import time

import pytest
from wd_config.discord import RestCache
from wd_discord.errors.api import ApiResponseError
from wd_discord.testing import RecordingClient


ROLES = "/guilds/1/roles"


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    now = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    return now


async def test_a_cached_read_is_reused() -> None:
    client = RecordingClient()
    client.reply("GET", ROLES, [])
    first = await client.get(t"/guilds/{1}/roles", cache=True)
    second = await client.get(t"/guilds/{1}/roles", cache=True)

    assert first is second
    assert len(client.requests_to("GET", ROLES)) == 1


async def test_a_read_without_cache_goes_out_again() -> None:
    client = RecordingClient()
    await client.get(t"/guilds/{1}/roles", cache=True)
    await client.get(t"/guilds/{1}/roles")

    assert len(client.requests_to("GET", ROLES)) == 2


async def test_a_cached_read_expires(clock: list[float]) -> None:
    client = RecordingClient()
    await client.get(t"/guilds/{1}/roles", cache=True)
    clock[0] += RestCache.ttl + 1
    await client.get(t"/guilds/{1}/roles", cache=True)

    assert len(client.requests_to("GET", ROLES)) == 2


async def test_a_write_under_the_same_guild_drops_it() -> None:
    client = RecordingClient()
    await client.get(t"/guilds/{1}/roles", cache=True)
    await client.post(t"/guilds/{1}/channels", json={"name": "new"})
    await client.get(t"/guilds/{1}/roles", cache=True)

    assert len(client.requests_to("GET", ROLES)) == 2


async def test_a_write_elsewhere_keeps_it() -> None:
    client = RecordingClient()
    await client.get(t"/guilds/{1}/roles", cache=True)
    await client.post(t"/guilds/{2}/channels", json={"name": "new"})
    await client.post(t"/channels/{1}/messages", json={"content": "hi"})
    await client.get(t"/guilds/{1}/roles", cache=True)

    assert len(client.requests_to("GET", ROLES)) == 1


async def test_a_failure_is_not_cached() -> None:
    client = RecordingClient()
    client.fail("GET", ROLES, ApiResponseError(code=50013, message="Missing Permissions", status=403))
    await client.get(t"/guilds/{1}/roles", cache=True)
    await client.get(t"/guilds/{1}/roles", cache=True)

    assert len(client.requests_to("GET", ROLES)) == 2


async def test_other_params_are_cached_apart() -> None:
    client = RecordingClient()
    await client.get(t"/guilds/{1}", cache=True, params={"with_counts": "true"})
    await client.get(t"/guilds/{1}", cache=True)

    assert len(client.requests_to("GET", "/guilds/1")) == 2
