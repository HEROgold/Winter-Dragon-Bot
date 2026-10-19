"""Live tests: read the bot's profile, and (opt-in) exercise the profile write path."""

from __future__ import annotations

lazy import os
lazy from typing import TYPE_CHECKING

lazy import pytest
lazy from wd_discord import is_network_error


if TYPE_CHECKING:
    lazy from collections.abc import Callable
    lazy from typing import Any

    lazy from wd_discord import Client

pytestmark = pytest.mark.integration


async def test_read_profile(client: Client, assert_success: Callable[[object], Any]) -> None:
    """GET /users/@me exposes the bot's profile fields."""
    profile = assert_success(await client.users.me())
    assert "username" in profile
    assert "id" in profile


@pytest.mark.skipif(
    not os.environ.get("WD_DISCORD_TEST_PROFILE_WRITE"),
    reason="Set WD_DISCORD_TEST_PROFILE_WRITE=1 to exercise the PATCH /users/@me write path.",
)
async def test_modify_username_idempotent(client: Client, assert_success: Callable[[object], Any]) -> None:
    """PATCH /users/@me with the *current* username - exercises the write path without changing anything."""
    me = await client.users.me()
    current = assert_success(me)
    assert not is_network_error(me)
    updated = assert_success(await me.edit(username=current["username"]))
    assert updated["username"] == current["username"]
