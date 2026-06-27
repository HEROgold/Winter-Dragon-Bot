"""Live test: connect the Gateway, identify, and send a presence/activity update."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from wd_discord import Activity, Gateway, GatewayActivity, Status


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from wd_discord import Client

pytestmark = pytest.mark.integration

CONNECT_TIMEOUT = 30


async def test_gateway_connect_and_update_presence(
    client: Client,
    token: str,
    assert_success: Callable[[object], Any],
) -> None:
    """Open the gateway WebSocket, await READY, then push an activity/status update."""
    info = assert_success(await client.get_gateway_bot())
    url = f"{info['url']}?v=10&encoding=json"

    gateway = Gateway(token, url=url)
    try:
        ready = await asyncio.wait_for(gateway.connect(), timeout=CONNECT_TIMEOUT)
        assert ready.session_id
        assert ready.resume_gateway_url.startswith("wss://")
        assert ready.user.get("bot") is True

        # Sending a presence update (op 3); a clean send (no exception) means it was accepted.
        await gateway.update_presence(
            [GatewayActivity("with wd-discord", Activity.CUSTOM, state="running tests")],
            Status.online,
        )
        # Let the heartbeat/ack cycle run briefly to surface any protocol error.
        await asyncio.sleep(2)
    finally:
        await gateway.close()
