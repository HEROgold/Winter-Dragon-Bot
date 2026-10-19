"""A minimal Discord Gateway (WebSocket) connection for wd-discord.

``httpxyz`` is REST-only, so the gateway uses the ``websockets`` library. This implements
just enough of the v10 gateway (https://docs.discord.com/developers/topics/gateway) to:

* connect and receive HELLO (op 10),
* heartbeat (op 1),
* IDENTIFY (op 2) with an optional initial presence,
* receive READY (op 0 / ``t == "READY"``), and
* send Presence Updates (op 3) - i.e. set the bot's activity/status, and
* keep the session alive: :meth:`Gateway.run` RESUMEs (op 6) after a reconnect request or a dropped socket,
  and IDENTIFYs again when Discord ends the session.

The presence/READY (de)serialisation is factored into the pure helpers
:func:`build_presence` and :func:`parse_ready` so they can be unit-tested without a socket.
"""

from __future__ import annotations

lazy import asyncio
lazy import json
lazy import random
lazy from dataclasses import dataclass
lazy from enum import Enum, IntEnum, auto
lazy from typing import TYPE_CHECKING, Any, Literal, NotRequired, Self, TypedDict, cast

lazy from herogold.log import LoggerMixin
lazy from wd_config.discord import URLS
lazy from wd_core.intents import Intents
lazy from wd_errors import Activity
lazy from websockets.asyncio.client import connect
lazy from websockets.exceptions import ConnectionClosed, InvalidHandshake

lazy from .dispatch import parse_dispatch
lazy from .events import EventName, Ready
lazy from .presence import Status


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Mapping

    lazy from websockets.asyncio.client import ClientConnection

    lazy from wd_discord.models import DiscordModel


class _DispatchFrame(TypedDict):
    """A DISPATCH (op 0) frame: the only frame with ``t`` set and a "real" ``d`` payload."""

    op: Literal[Opcode.DISPATCH]
    t: str
    s: int
    d: Mapping[str, object]


class _HeartbeatRequestFrame(TypedDict):
    """Discord asking for an out-of-cycle heartbeat (op 1, server -> client)."""

    op: Literal[Opcode.HEARTBEAT]
    s: NotRequired[int | None]


class _ReconnectFrame(TypedDict):
    """Discord asking the client to reconnect (op 7)."""

    op: Literal[Opcode.RECONNECT]
    s: NotRequired[int | None]


class _InvalidSessionFrame(TypedDict):
    """The session is invalid (op 9); ``d`` says whether it's resumable."""

    op: Literal[Opcode.INVALID_SESSION]
    d: NotRequired[bool]
    s: NotRequired[int | None]


class _HeartbeatAckFrame(TypedDict):
    """Discord acknowledging our heartbeat (op 11)."""

    op: Literal[Opcode.HEARTBEAT_ACK]
    s: NotRequired[int | None]


type GatewayFrame = _DispatchFrame | _HeartbeatRequestFrame | _ReconnectFrame | _InvalidSessionFrame | _HeartbeatAckFrame
"""Every frame shape :meth:`Gateway.listen` can receive (post-READY; HELLO/IDENTIFY are handled
inline by :meth:`Gateway.connect` and never reach ``listen``)."""


class Opcode(IntEnum):
    """Discord gateway opcodes (the subset this client uses).

    https://docs.discord.com/developers/topics/opcodes-and-status-codes#gateway-gateway-opcodes
    """

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


FATAL_CLOSE_CODES = frozenset({4004, 4010, 4011, 4012, 4013, 4014})
"""Close codes reconnecting can't fix: bad token, shard, API version or intents
(https://docs.discord.com/developers/topics/opcodes-and-status-codes#gateway-gateway-close-event-codes)."""
NEW_SESSION_CLOSE_CODES = frozenset({4007, 4009})
"""Close codes after which the session can't be resumed, only replaced: invalid sequence, session timed out
(https://docs.discord.com/developers/topics/opcodes-and-status-codes#gateway-gateway-close-event-codes)."""
MAX_RESUME_ATTEMPTS = 5
"""Failed attempts to reach the resume URL before giving up on the session and identifying a new one."""


class Disconnect(Enum):
    """Why :meth:`Gateway.listen` stopped, and so how :meth:`Gateway.run` reconnects."""

    RESUME = auto()
    """Discord asked for a reconnect, or the socket dropped: resume the session, missing no events."""
    IDENTIFY = auto()
    """Discord ended the session: identify a new one."""


class GatewayClosedError(RuntimeError):
    """Discord closed the gateway with a code reconnecting can't fix (see :data:`FATAL_CLOSE_CODES`)."""

    def __init__(self, code: int, reason: str) -> None:
        """Record Discord's close ``code`` and ``reason``."""
        super().__init__(f"Discord closed the gateway with {code}: {reason}")
        self.code = code


@dataclass
class GatewayActivity:
    """An activity shown on the bot's presence (object -> API via :meth:`to_dict`)."""

    name: str
    type: Activity = Activity.PLAYING
    url: str | None = None
    state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the Discord activity object."""
        data: dict[str, Any] = {"name": self.name, "type": int(self.type)}
        if self.url is not None:
            data["url"] = self.url
        if self.state is not None:
            data["state"] = self.state
        return data


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
    intents: Intents,
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
    shard = data.get("shard")
    return Ready.model_validate(
        {
            "v": data.get("v", 10),
            "user": data["user"],
            "guilds": data.get("guilds", []),
            "session_id": data["session_id"],
            "resume_gateway_url": data["resume_gateway_url"],
            "shard": tuple(shard) if shard else None,
            "application_id": data.get("application", {}).get("id"),
        },
    )


class Gateway(LoggerMixin):
    """A minimal async Discord gateway client."""

    def __init__(
        self,
        token: str,
        *,
        intents: Intents | None = None,
        url: str | None = None,
        shard: tuple[int, int] | None = None,
    ) -> None:
        """Create a gateway for ``token`` with the given ``intents`` (default: none).

        ``url`` defaults to :attr:`~wd_config.discord.URLS.gateway_url`, the configured host and API version.
        ``shard`` is the ``(shard_id, num_shards)`` pair sent in IDENTIFY when sharding.
        """
        self.token = token
        self.intents = intents or Intents.none()
        self.url = url if url is not None else URLS().gateway_url
        self.shard = shard
        self._ws: ClientConnection | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._seq: int | None = None
        self._presence: dict[str, Any] | None = None
        self._ready_dispatched = False
        self.ready: Ready | None = None
        self.reidentify_delay = (1.0, 5.0)
        """Seconds to wait, picked at random in this range, before identifying again (Discord asks for 1-5)."""
        self.resume_backoff = 1.0
        """Seconds before the first retry of a failed resume; each retry doubles it."""

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
        self._presence = presence
        ws = await self._open(self.url)
        await self._send(
            Opcode.IDENTIFY,
            build_identify(self.token, self.intents, shard=self.shard, presence=presence),
        )

        while True:
            message = json.loads(await ws.recv())
            if (seq := message.get("s")) is not None:
                self._seq = seq
            if message["op"] == Opcode.DISPATCH and message.get("t") == "READY":
                self.ready = parse_ready(message)
                self._ready_dispatched = False
                return self.ready

    async def _open(self, url: str) -> ClientConnection:
        """Connect to ``url``, wait for HELLO, start heartbeating at the interval it names, and return the socket."""
        ws = self._ws = await connect(url)
        hello = json.loads(await ws.recv())
        interval = hello["d"]["heartbeat_interval"] / 1000
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))
        return ws

    async def resume(self) -> None:
        """Reconnect to the session's resume URL and RESUME (op 6) it from the last sequence received.

        Discord then replays the events missed since, and sends RESUMED; or INVALID_SESSION when it can't.
        https://docs.discord.com/developers/events/gateway#resuming
        """
        if self.ready is None:
            msg = "There is no session to resume."
            raise RuntimeError(msg)
        await self._open(f"{self.ready.resume_gateway_url}/{URLS().gateway_query}")
        await self._send(Opcode.RESUME, {"token": self.token, "session_id": self.ready.session_id, "seq": self._seq})

    async def run(self, dispatch: Callable[[str, DiscordModel], Awaitable[None]]) -> None:
        """Run :meth:`listen` until cancelled, reconnecting whenever the connection ends.

        A reconnect request or a dropped socket resumes the session (retrying with backoff, then identifying a
        new one); an ended session waits :attr:`reidentify_delay` and identifies again, which dispatches a new
        READY. Raises :class:`GatewayClosedError` on a close code reconnecting can't fix.
        """
        while True:
            reason = await self.listen(dispatch)
            await self.close()
            if reason is Disconnect.RESUME and await self._resume_with_retries():
                continue
            await asyncio.sleep(random.uniform(*self.reidentify_delay))  # noqa: S311 - jitter, not crypto
            await self.connect(presence=self._presence)

    async def _resume_with_retries(self) -> bool:
        """Try :meth:`resume` up to :data:`MAX_RESUME_ATTEMPTS` times; ``False`` if every attempt failed."""
        if self.ready is None:
            return False
        for attempt in range(MAX_RESUME_ATTEMPTS):
            try:
                await self.resume()
            except (OSError, ConnectionClosed, InvalidHandshake) as error:
                self.logger.warning(t"Resume attempt {attempt + 1} failed: {error!r}")
                await self.close()
                await asyncio.sleep(self.resume_backoff * 2**attempt)
            else:
                return True
        return False

    async def listen(self, dispatch: Callable[[str, DiscordModel], Awaitable[None]]) -> Disconnect:
        """Receive frames, updating ``_seq`` and invoking ``dispatch`` on DISPATCH, until the connection ends.

        Must be called after :meth:`connect` has returned (i.e. after READY). The READY that :meth:`connect`
        consumed is dispatched first, once per session, so a resumed session doesn't repeat it. Returns how to
        reconnect when Discord sends RECONNECT/INVALID_SESSION or the socket closes; raises
        :class:`GatewayClosedError` on a close code reconnecting can't fix. :meth:`run` does the reconnecting.
        """
        if self._ws is None:
            msg = "Gateway is not connected."
            raise RuntimeError(msg)
        if self.ready is not None and not self._ready_dispatched:
            self._ready_dispatched = True
            await dispatch(EventName.READY, self.ready)
        while True:
            try:
                raw = await self._ws.recv()
            except ConnectionClosed as closed:
                return self._closed(closed)
            disconnect = await self._handle(cast("GatewayFrame", json.loads(raw)), dispatch)
            if disconnect is not None:
                return disconnect

    async def _handle(
        self,
        message: GatewayFrame,
        dispatch: Callable[[str, DiscordModel], Awaitable[None]],
    ) -> Disconnect | None:
        """Act on one frame; return how to reconnect when it ends the connection."""
        if (seq := message.get("s")) is not None:
            self._seq = seq
        match message:
            case {"op": Opcode.DISPATCH}:
                await dispatch(message["t"], parse_dispatch(message["t"], message["d"]))
            case {"op": Opcode.HEARTBEAT}:
                await self._send(Opcode.HEARTBEAT, self._seq)
            case {"op": Opcode.RECONNECT}:
                self.logger.info(t"Gateway requested a reconnect; resuming.")
                return Disconnect.RESUME
            case {"op": Opcode.INVALID_SESSION}:
                resumable = bool(message.get("d"))
                self.logger.warning(t"Gateway invalidated the session (resumable: {resumable}).")
                return Disconnect.RESUME if resumable else Disconnect.IDENTIFY
            case _:
                pass
        return None

    def _closed(self, closed: ConnectionClosed) -> Disconnect:
        """Decide how to reconnect after the socket closed with ``closed``'s code."""
        code = None if closed.rcvd is None else closed.rcvd.code
        reason = "" if closed.rcvd is None else closed.rcvd.reason
        if code in FATAL_CLOSE_CODES:
            raise GatewayClosedError(code, reason)
        self.logger.warning(t"Gateway connection closed ({code}: {reason}).")
        return Disconnect.IDENTIFY if code in NEW_SESSION_CLOSE_CODES else Disconnect.RESUME

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
