"""Live test: the headline check - take a bot token and connect to the Discord API."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from wd_discord import Client

pytestmark = pytest.mark.integration


async def test_connect_returns_bot_user(client: Client, assert_success: Callable[[object], Any]) -> None:
    """Connecting with the token and hitting GET /users/@me returns the bot user."""
    user = assert_success(await client.get_current_user())
    assert "id" in user
    assert user.get("bot") is True


def test_client_targets_v10(client: Client) -> None:
    """The client is pinned to the v10 REST API."""
    assert client.base_url.endswith("/v10")
