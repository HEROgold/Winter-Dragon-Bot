"""Live tests: read-only connectivity to each major Discord v10 REST concept."""
from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy import pytest


if TYPE_CHECKING:
    lazy from collections.abc import Callable
    lazy from typing import Any

    lazy from wd_discord import Client

pytestmark = pytest.mark.integration


async def test_current_user(client: Client, assert_success: Callable[[object], Any]) -> None:
    """User resource: GET /users/@me."""
    assert "id" in assert_success(await client.get_current_user())


async def test_current_application(client: Client, assert_success: Callable[[object], Any]) -> None:
    """Application resource: GET /applications/@me."""
    assert "id" in assert_success(await client.get_current_application())


async def test_gateway_bot(client: Client, assert_success: Callable[[object], Any]) -> None:
    """Gateway resource: GET /gateway/bot returns a wss URL + session limits."""
    data = assert_success(await client.get_gateway_bot())
    assert data["url"].startswith("wss://")
    assert "session_start_limit" in data


async def test_guild(
    client: Client,
    support_guild_id: str | None,
    assert_success: Callable[[object], Any],
) -> None:
    """Guild resource: GET /guilds/{id} for the configured support guild."""
    if not support_guild_id:
        pytest.skip("No support_guild_id configured in config.ini.")
    data = assert_success(await client.get_guild(support_guild_id))
    assert str(data["id"]) == support_guild_id


async def test_channel(
    client: Client,
    support_guild_id: str | None,
    assert_success: Callable[[object], Any],
) -> None:
    """Channel resource: list the guild's channels, then GET /channels/{id} for one."""
    if not support_guild_id:
        pytest.skip("No support_guild_id configured in config.ini.")
    channels = assert_success(await client.get(f"/guilds/{support_guild_id}/channels"))
    assert channels, "support guild has no channels to read"
    channel = assert_success(await client.get_channel(channels[0]["id"]))
    assert "id" in channel
