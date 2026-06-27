"""Live tests: read the bot's profile, and (opt-in) exercise the profile write path."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from wd_discord import Client

pytestmark = pytest.mark.integration


async def test_read_profile(client: Client, assert_success: Callable[[object], Any]) -> None:
    """GET /users/@me exposes the bot's profile fields."""
    profile = assert_success(await client.get_current_user())
    assert "username" in profile
    assert "id" in profile


@pytest.mark.skipif(
    not os.environ.get("WD_DISCORD_TEST_PROFILE_WRITE"),
    reason="Set WD_DISCORD_TEST_PROFILE_WRITE=1 to exercise the PATCH /users/@me write path.",
)
async def test_modify_username_idempotent(client: Client, assert_success: Callable[[object], Any]) -> None:
    """PATCH /users/@me with the *current* username - exercises the write path without changing anything."""
    current = assert_success(await client.get_current_user())
    updated = assert_success(await client.modify_current_user(username=current["username"]))
    assert updated["username"] == current["username"]
