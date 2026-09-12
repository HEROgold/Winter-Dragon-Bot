"""Unit tests: dispatch-event parsing (:mod:`wd_discord.gateway.events`) and the continuous
receive loop (:meth:`Gateway.listen`), no real socket involved.
"""

from __future__ import annotations

lazy import json
lazy from typing import Any

lazy import pytest
lazy from wd_discord.gateway import EventName, GuildCreate, Message, RawEvent, parse_dispatch
lazy from wd_discord.gateway.connection import Gateway, Opcode


def test_event_name_members_match_discord_wire_format() -> None:
    assert EventName.MESSAGE_CREATE == "MESSAGE_CREATE"
    assert EventName.GUILD_CREATE == "GUILD_CREATE"


def test_event_name_members_carry_their_own_model() -> None:
    assert EventName.MESSAGE_CREATE.model is Message
    assert EventName.GUILD_CREATE.model is GuildCreate


def test_event_name_covers_every_dispatch_event_except_ready() -> None:
    assert "READY" not in EventName.__members__
    assert len(EventName) > 70  # the full Discord catalog, not just the two modeled events


def test_event_name_unmodeled_members_have_no_model_yet() -> None:
    assert EventName.MESSAGE_UPDATE.model is None
    assert EventName.TYPING_START.model is None


def test_parse_dispatch_falls_back_to_raw_event_for_known_but_unmodeled_name() -> None:
    """A member with no model yet still dispatches, just as RawEvent, not a crash."""
    event = parse_dispatch(EventName.MESSAGE_UPDATE, {"id": "1", "content": "edited"})
    assert isinstance(event, RawEvent)
    assert event.name == "MESSAGE_UPDATE"
    assert event.data == {"id": "1", "content": "edited"}


def test_parse_dispatch_message_create() -> None:
    event = parse_dispatch(
        EventName.MESSAGE_CREATE,
        {
            "id": "1",
            "channel_id": "2",
            "author": {"id": "3", "username": "bot", "discriminator": "0"},
            "content": "hi",
            "timestamp": "t",
            "tts": False,
            "mention_everyone": False,
        },
    )
    assert isinstance(event, Message)
    assert event.content == "hi"
    assert event.author.username == "bot"


def test_parse_dispatch_guild_create() -> None:
    event = parse_dispatch(EventName.GUILD_CREATE, {"id": "1", "name": "My Guild", "owner_id": "9"})
    assert isinstance(event, GuildCreate)
    assert event.name == "My Guild"
    assert event.channels == []


def test_parse_dispatch_accepts_plain_str_matching_an_event_name() -> None:
    """Gateway.listen() only ever has a plain ``str`` off the socket, not an EventName member."""
    event = parse_dispatch(
        "MESSAGE_CREATE",
        {
            "id": "1",
            "channel_id": "2",
            "author": {"id": "3", "username": "bot", "discriminator": "0"},
            "content": "hi",
            "timestamp": "t",
            "tts": False,
            "mention_everyone": False,
        },
    )
    assert isinstance(event, Message)


def test_parse_dispatch_falls_back_to_raw_event() -> None:
    event = parse_dispatch("SOMETHING_UNMODELED", {"foo": "bar"})
    assert isinstance(event, RawEvent)
    assert event.name == "SOMETHING_UNMODELED"
    assert event.data == {"foo": "bar"}


class _EndOfFrames(Exception):
    """Sentinel raised by :class:`FakeWebSocket` once its canned frames are exhausted."""


class FakeWebSocket:
    """Stands in for a websockets ClientConnection: replays canned JSON frames."""

    def __init__(self, frames: list[dict[str, Any]]) -> None:
        self._frames = [json.dumps(frame) for frame in frames]
        self.sent: list[str] = []

    async def recv(self) -> str:
        if not self._frames:
            raise _EndOfFrames
        return self._frames.pop(0)

    async def send(self, data: str) -> None:
        self.sent.append(data)


async def test_listen_dispatches_and_tracks_sequence() -> None:
    gateway = Gateway("token")
    gateway._ws = FakeWebSocket(
        [
            {
                "op": Opcode.DISPATCH,
                "s": 1,
                "t": "MESSAGE_CREATE",
                "d": {
                    "id": "1",
                    "channel_id": "2",
                    "author": {"id": "3", "username": "bot", "discriminator": "0"},
                    "content": "hi",
                    "timestamp": "t",
                    "tts": False,
                    "mention_everyone": False,
                },
            },
            {"op": Opcode.DISPATCH, "s": 2, "t": "SOMETHING_UNMODELED", "d": {"foo": "bar"}},
        ],
    )

    received: list[tuple[str, Any]] = []

    async def dispatch(name: str, payload: Any) -> None:  # noqa: ANN401
        received.append((name, payload))

    with pytest.raises(_EndOfFrames):
        await gateway.listen(dispatch)

    assert gateway._seq == 2  # noqa: SLF001 - test assertion
    assert received[0][0] == "MESSAGE_CREATE"
    assert isinstance(received[0][1], Message)
    assert received[1][0] == "SOMETHING_UNMODELED"
    assert isinstance(received[1][1], RawEvent)


async def test_listen_replies_to_heartbeat_request() -> None:
    gateway = Gateway("token")
    ws = FakeWebSocket([{"op": Opcode.HEARTBEAT, "s": None}])
    gateway._ws = ws  # noqa: SLF001 - test wiring

    async def dispatch(name: str, payload: Any) -> None:  # noqa: ANN401
        pass

    with pytest.raises(_EndOfFrames):
        await gateway.listen(dispatch)

    assert len(ws.sent) == 1
    assert json.loads(ws.sent[0])["op"] == Opcode.HEARTBEAT


async def test_listen_returns_on_reconnect_request() -> None:
    gateway = Gateway("token")
    gateway._ws = FakeWebSocket([{"op": Opcode.RECONNECT, "s": None}])  # noqa: SLF001 - test wiring

    async def dispatch(name: str, payload: Any) -> None:  # noqa: ANN401
        pass

    await gateway.listen(dispatch)  # returns cleanly, does not raise
