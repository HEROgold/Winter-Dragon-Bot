"""A minimal Discord Gateway (WebSocket) connection for wd-discord.

``httpxyz`` is REST-only, so the gateway uses the ``websockets`` library. This implements
just enough of the v10 gateway (https://docs.discord.com/developers/topics/gateway) to:

* connect and receive HELLO (op 10),
* heartbeat (op 1),
* IDENTIFY (op 2) with an optional initial presence,
* receive READY (op 0 / ``t == "READY"``), and
* send Presence Updates (op 3) - i.e. set the bot's activity/status.

The presence/READY (de)serialisation is factored into the pure helpers
:func:`build_presence` and :func:`parse_ready` so they can be unit-tested without a socket.
"""
from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Any, Self

from pydantic import Field
from wd_errors import Activity
from websockets.asyncio.client import connect

from wd_discord.models import DiscordModel


if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

# Default well-known gateway URL, already pinned to API v10 + JSON encoding.
DEFAULT_GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"


class Opcode(IntEnum):
    """Discord gateway opcodes (the subset this client uses)."""

    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE_UPDATE = 3
    RESUME = 6
    RECONNECT = 7
    REQUEST_GUILD_MEMBERS = 8
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11


class Status(StrEnum):
    """Valid presence statuses (https://docs.discord.com/developers/topics/gateway-events#update-presence-status-types)."""

    online = "online"
    dnd = "dnd"
    idle = "idle"
    invisible = "invisible"
    offline = "offline"


@dataclass
class GatewayActivity:
    """An activity shown on the bot's presence (object -> API via :meth:`to_dict`)."""

    name: str
    type: Activity = Activity.PLAYING
    url: str | None = None
    state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the Discord activity object."""
        data: dict[str, Any] = {"name": self.name, "type": int(self.type)}
        if self.url is not None:
            data["url"] = self.url
        if self.state is not None:
            data["state"] = self.state
        return data


class Ready(DiscordModel):
    """The parts of a READY dispatch we care about (API -> object via :func:`parse_ready`)."""

    session_id: str
    resume_gateway_url: str
    user: dict[str, Any] = Field(default_factory=dict) # Could we make this a User object?
    application_id: str | None = None


def build_presence(
    activities: list[GatewayActivity],
    status: Status | str = Status.online,
    *,
    afk: bool = False,
    since: int | None = None,
) -> dict[str, Any]:
    """Build the ``d`` payload for a Presence Update (object -> API)."""
    return {
        "since": since,
        "activities": [activity.to_dict() for activity in activities],
        "status": str(status),
        "afk": afk,
    }


def build_identify(
    token: str,
    intents: int,
    *,
    shard: tuple[int, int] | None = None,
    presence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the ``d`` payload for an IDENTIFY (object -> API).

    ``shard`` is Discord's ``[shard_id, num_shards]`` pair (zero-based); omitted when not sharding
    (https://docs.discord.com/developers/events/gateway#sharding).
    """
    data: dict[str, Any] = {
        "token": token,
        "intents": intents,
        "properties": {"os": "linux", "browser": "wd-discord", "device": "wd-discord"},
        "presence": presence,
    }
    if shard is not None:
        data["shard"] = list(shard)
    return data


def parse_ready(payload: dict[str, Any]) -> Ready:
    """Parse a READY dispatch payload into a :class:`Ready` (API -> object)."""
    data = payload.get("d", payload)
    return Ready(
        session_id=data["session_id"],
        resume_gateway_url=data["resume_gateway_url"],
        user=data.get("user", {}),
        application_id=data.get("application", {}).get("id"),
    )


class Gateway:
    """A minimal async Discord gateway client."""

    def __init__(
        self,
        token: str,
        *,
        intents: int = 0,
        url: str = DEFAULT_GATEWAY_URL,
        shard: tuple[int, int] | None = None,
    ) -> None:
        """Create a gateway for ``token`` with the given ``intents`` (default: none).

        ``shard`` is the ``(shard_id, num_shards)`` pair sent in IDENTIFY when sharding.
        """
        self.token = token
        self.intents = intents
        self.url = url
        self.shard = shard
        self._ws: ClientConnection | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._seq: int | None = None
        self.ready: Ready | None = None

    async def _send(self, op: Opcode, data: Any) -> None:  # noqa: ANN401
        """Send a gateway payload."""
        if self._ws is None:
            msg = "Gateway is not connected."
            raise RuntimeError(msg)
        await self._ws.send(json.dumps({"op": int(op), "d": data}))

    async def _heartbeat_loop(self, interval: float) -> None:
        """Send op 1 heartbeats every ``interval`` seconds with the last sequence.

        The first beat waits ``interval * jitter`` (random in [0, 1)) as required by
        https://docs.discord.com/developers/events/gateway#sending-heartbeats.
        """
        await asyncio.sleep(interval * random.random())  # noqa: S311
        while True:
            await self._send(Opcode.HEARTBEAT, self._seq)
            await asyncio.sleep(interval)

    async def connect(
        self,
        *,
        presence: dict[str, Any] | None = None,
    ) -> Ready:
        """Open the connection, identify, and return once READY is received."""
        self._ws = await connect(self.url)

        hello = json.loads(await self._ws.recv())
        interval = hello["d"]["heartbeat_interval"] / 1000
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))

        await self._send(
            Opcode.IDENTIFY,
            build_identify(self.token, self.intents, shard=self.shard, presence=presence),
        )

        while True:
            message = json.loads(await self._ws.recv())
            if (seq := message.get("s")) is not None:
                self._seq = seq
            if message["op"] == Opcode.DISPATCH and message.get("t") == "READY":
                self.ready = parse_ready(message)
                return self.ready

    async def update_presence(
        self,
        activities: list[GatewayActivity],
        status: Status | str = Status.online,
    ) -> None:
        """Send a Presence Update (op 3) to set the bot's activity/status."""
        await self._send(Opcode.PRESENCE_UPDATE, build_presence(activities, status))

    async def close(self) -> None:
        """Cancel the heartbeat and close the WebSocket."""
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:  # noqa: SIM105
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def __aenter__(self) -> Self:
        """Connect on context entry."""
        await self.connect()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close on context exit."""
        await self.close()
