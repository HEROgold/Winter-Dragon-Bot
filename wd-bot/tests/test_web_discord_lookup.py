"""Unit tests: the dashboard's Discord name lookup and its cache, on a recording client (no network)."""

from datetime import UTC, datetime, timedelta

import pytest
from wd_discord.errors.api import ApiResponseError
from wd_discord.snowflake import Snowflake
from wd_discord.testing import RecordingClient, user_json

from winter_dragon.web.discord_lookup import CACHE_LIFETIME, DiscordLookup, named_user
from winter_dragon.web.references import LookupStatus


USER = Snowflake(7)


class Clock:
    def __init__(self) -> None:
        self.moment = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.moment


@pytest.fixture
def clock() -> Clock:
    return Clock()


def lookup_on(client: RecordingClient, clock: Clock) -> DiscordLookup:
    lookup = DiscordLookup("token", now=clock)
    lookup._client = client  # noqa: SLF001 - skip opening a real connection
    return lookup


async def test_user_is_named_by_display_name(clock: Clock) -> None:
    client = RecordingClient()
    client.reply("GET", "/users/7", user_json(id="7", global_name="Someone"))

    named = named_user(await lookup_on(client, clock).user(USER))

    assert named.status is LookupStatus.FOUND
    assert named.name == "Someone"


async def test_a_found_user_is_asked_for_once_per_lifetime(clock: Clock) -> None:
    client = RecordingClient()
    client.reply("GET", "/users/7", user_json(id="7", global_name="Someone"))
    lookup = lookup_on(client, clock)

    await lookup.user(USER)
    clock.moment += CACHE_LIFETIME - timedelta(seconds=1)
    await lookup.user(USER)
    assert len(client.requests_to("GET", "/users/7")) == 1

    clock.moment += timedelta(seconds=2)
    await lookup.user(USER)
    assert len(client.requests_to("GET", "/users/7")) == 2


async def test_an_unknown_user_is_unknown_and_cached(clock: Clock) -> None:
    client = RecordingClient()
    client.reply("GET", "/users/7", {"code": 10013, "message": "Unknown User"}, status=404)
    lookup = lookup_on(client, clock)

    first = await lookup.user(USER)
    await lookup.user(USER)

    assert first.status is LookupStatus.UNKNOWN
    assert len(client.requests_to("GET", "/users/7")) == 1


async def test_an_unavailable_lookup_is_not_cached(clock: Clock) -> None:
    client = RecordingClient()
    client.fail("GET", "/users/7", ApiResponseError(code=0, message="Rate limited", status=429))
    lookup = lookup_on(client, clock)

    first = await lookup.user(USER)
    await lookup.user(USER)

    assert first.status is LookupStatus.UNAVAILABLE
    assert len(client.requests_to("GET", "/users/7")) == 2


async def test_unopened_lookup_refuses_to_ask() -> None:
    with pytest.raises(RuntimeError, match="async with"):
        await DiscordLookup("token").user(USER)
