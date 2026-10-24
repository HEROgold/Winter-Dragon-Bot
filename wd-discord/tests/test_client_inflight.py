"""Unit tests: identical GETs in flight at once share one request; anything else goes out on its own."""

import asyncio
from typing import TYPE_CHECKING

import pytest
from httpxyz import AsyncClient, ConnectError, MockTransport, Request, Response
from wd_discord import Client


if TYPE_CHECKING:
    from collections.abc import Callable


class Gate:
    """A transport that holds every request until :meth:`open`, counting what was sent."""

    def __init__(self, fail: Callable[[Request], Exception] | None = None) -> None:
        self.sent: list[Request] = []
        self.released = asyncio.Event()
        self.fail = fail

    async def __call__(self, request: Request) -> Response:
        self.sent.append(request)
        await self.released.wait()
        if self.fail is not None:
            raise self.fail(request)
        return Response(200, json={"path": request.url.path})

    def open(self) -> None:
        self.released.set()


@pytest.fixture
def gate() -> Gate:
    return Gate()


def client_through(gate: Gate) -> Client:
    client = Client("token")
    client._client = AsyncClient(base_url=client.base_url, transport=MockTransport(gate))  # noqa: SLF001 - swap the transport
    return client


async def settle() -> None:
    """Let every started request reach the transport."""
    for _ in range(5):
        await asyncio.sleep(0)


async def test_concurrent_identical_gets_share_one_request(gate: Gate) -> None:
    client = client_through(gate)
    first = asyncio.create_task(client.get(t"/guilds/{1}/roles"))
    second = asyncio.create_task(client.get(t"/guilds/{1}/roles"))
    await settle()
    gate.open()

    assert await first is await second
    assert len(gate.sent) == 1


async def test_params_in_another_order_are_the_same_read(gate: Gate) -> None:
    client = client_through(gate)
    first = asyncio.create_task(client.get(t"/guilds/{1}/members", params={"limit": "5", "after": "0"}))
    second = asyncio.create_task(client.get(t"/guilds/{1}/members", params={"after": "0", "limit": "5"}))
    await settle()
    gate.open()
    await asyncio.gather(first, second)

    assert len(gate.sent) == 1


async def test_other_params_are_another_read(gate: Gate) -> None:
    client = client_through(gate)
    first = asyncio.create_task(client.get(t"/guilds/{1}/members", params={"after": "0"}))
    second = asyncio.create_task(client.get(t"/guilds/{1}/members", params={"after": "9"}))
    await settle()
    gate.open()
    await asyncio.gather(first, second)

    assert len(gate.sent) == 2


async def test_a_finished_read_is_not_reused(gate: Gate) -> None:
    client = client_through(gate)
    gate.open()
    await client.get(t"/guilds/{1}/roles")
    await client.get(t"/guilds/{1}/roles")

    assert len(gate.sent) == 2


async def test_writes_are_never_shared(gate: Gate) -> None:
    client = client_through(gate)
    first = asyncio.create_task(client.post(t"/channels/{1}/messages", json={"content": "hi"}))
    second = asyncio.create_task(client.post(t"/channels/{1}/messages", json={"content": "hi"}))
    await settle()
    gate.open()
    await asyncio.gather(first, second)

    assert len(gate.sent) == 2


async def test_a_get_with_headers_goes_out_on_its_own(gate: Gate) -> None:
    client = client_through(gate)
    first = asyncio.create_task(client.get(t"/guilds/{1}/roles"))
    second = asyncio.create_task(client.get(t"/guilds/{1}/roles", headers={"X-Audit-Log-Reason": "x"}))
    await settle()
    gate.open()
    await asyncio.gather(first, second)

    assert len(gate.sent) == 2


async def test_cancelling_one_caller_leaves_the_read_for_the_others(gate: Gate) -> None:
    client = client_through(gate)
    first = asyncio.create_task(client.get(t"/guilds/{1}/roles"))
    second = asyncio.create_task(client.get(t"/guilds/{1}/roles"))
    await settle()
    first.cancel()
    await settle()
    gate.open()

    result = await second
    assert isinstance(result, Response)
    assert result.is_success
    assert len(gate.sent) == 1


async def test_a_network_error_reaches_every_caller_as_a_value() -> None:
    gate = Gate(fail=lambda request: ConnectError("down", request=request))
    client = client_through(gate)
    first = asyncio.create_task(client.get(t"/guilds/{1}/roles"))
    second = asyncio.create_task(client.get(t"/guilds/{1}/roles"))
    await settle()
    gate.open()

    results = await asyncio.gather(first, second)
    assert all(isinstance(result, ConnectError) for result in results)
    assert len(gate.sent) == 1
