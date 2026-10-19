"""Live test: connect the Gateway, identify, and send a presence/activity update."""

from __future__ import annotations

lazy import asyncio
lazy from typing import TYPE_CHECKING

lazy import pytest
lazy from wd_config.discord import URLS
lazy from wd_discord import Gateway, GatewayActivity, Status
lazy from wd_errors import Activity


if TYPE_CHECKING:
    lazy from collections.abc import Callable
    lazy from typing import Any

    lazy from wd_discord import Client

pytestmark = pytest.mark.integration

CONNECT_TIMEOUT = 30


async def test_gateway_connect_and_update_presence(
    client: Client,
    token: str,
    assert_success: Callable[[object], Any],
) -> None:
    """Open the gateway WebSocket, await READY, then push an activity/status update."""
    info = assert_success(await client.get_gateway_bot())
    gateway = Gateway(token, url=f"{info['url']}{URLS().gateway_query}")
    try:
        ready = await asyncio.wait_for(gateway.connect(), timeout=CONNECT_TIMEOUT)
        assert ready.session_id
        assert ready.resume_gateway_url.startswith("wss://")
        assert ready.user.bot is True

        # Sending a presence update (op 3); a clean send (no exception) means it was accepted.
        await gateway.update_presence(
            [GatewayActivity("with wd-discord", Activity.CUSTOM, state="running tests")],
            Status.online,
        )
        # Let the heartbeat/ack cycle run briefly to surface any protocol error.
        await asyncio.sleep(2)
    finally:
        await gateway.close()
