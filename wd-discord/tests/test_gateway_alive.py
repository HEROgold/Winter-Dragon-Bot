"""Unit tests: Gateway.alive and ShardManager.alive follow the heartbeat acknowledgements."""

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from wd_discord.gateway.connection import Gateway, Opcode
from wd_discord.gateway.sharding import ShardManager


if TYPE_CHECKING:
    from wd_discord.gateway.connection import GatewayFrame
    from wd_discord.gateway.sharding import GatewayBotInfo


HEARTBEAT_ACK = {"op": Opcode.HEARTBEAT_ACK}


async def _never(*_: object) -> None:
    raise AssertionError


def _gateway(interval: float = 41.25) -> Gateway:
    gateway = Gateway("token")
    gateway._heartbeat_interval = interval  # noqa: SLF001 - what HELLO sets
    return gateway


async def test_a_gateway_without_an_acknowledged_heartbeat_is_not_alive() -> None:
    assert not _gateway().alive


async def test_an_acknowledged_heartbeat_makes_the_gateway_alive() -> None:
    gateway = _gateway()

    await gateway._handle(cast("GatewayFrame", HEARTBEAT_ACK), _never)  # noqa: SLF001

    assert gateway.alive


async def test_a_gateway_whose_last_ack_is_two_intervals_old_is_not_alive() -> None:
    gateway = _gateway(interval=10)
    gateway._last_ack = asyncio.get_running_loop().time() - 20  # noqa: SLF001

    assert not gateway.alive


def _manager(*shards: Gateway) -> ShardManager:
    manager = ShardManager("token", cast("GatewayBotInfo", SimpleNamespace(shards=len(shards))))
    manager.shards = list(shards)
    return manager


async def test_a_manager_is_alive_only_while_every_shard_is() -> None:
    alive, dead = _gateway(), _gateway()
    await alive._handle(cast("GatewayFrame", HEARTBEAT_ACK), _never)  # noqa: SLF001

    assert _manager(alive).alive
    assert not _manager(alive, dead).alive


async def test_a_manager_without_shards_is_not_alive() -> None:
    assert not _manager().alive
