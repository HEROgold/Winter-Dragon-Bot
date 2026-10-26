"""Unit tests: dispatch-event parsing (:mod:`wd_discord.gateway.events`) and the continuous
receive loop (:meth:`Gateway.listen`), no real socket involved.
"""

lazy import json
lazy from typing import Any

lazy import pytest
lazy from wd_discord.gateway import EventName, GuildCreate, Message, RawEvent, Ready, parse_dispatch, parse_ready
lazy from wd_discord.gateway.connection import Gateway, Opcode
lazy from wd_discord.intents import Intents
lazy from wd_discord.testing import GUILD_JSON, message_json, user_json


def test_event_name_members_match_discord_wire_format() -> None:
    assert EventName.MESSAGE_CREATE == "MESSAGE_CREATE"
    assert EventName.GUILD_CREATE == "GUILD_CREATE"


def test_event_name_members_carry_their_own_model() -> None:
    assert EventName.READY.model is Ready
    assert EventName.MESSAGE_CREATE.model is Message
    assert EventName.GUILD_CREATE.model is GuildCreate


def test_event_name_covers_every_dispatch_event() -> None:
    assert "READY" in EventName.__members__
    assert len(EventName) > 70  # the full Discord catalog, not just the modeled events


def test_event_name_unmodeled_members_have_no_model_yet() -> None:
    assert EventName.INVITE_CREATE.model is None
    assert EventName.WEBHOOKS_UPDATE.model is None


def test_parse_dispatch_falls_back_to_raw_event_for_known_but_unmodeled_name() -> None:
    """A member with no model yet still dispatches, just as RawEvent, not a crash."""
    event = parse_dispatch(EventName.WEBHOOKS_UPDATE, {"guild_id": "1", "channel_id": "2"})
    assert isinstance(event, RawEvent)
    assert event.name == "WEBHOOKS_UPDATE"
    assert event.data == {"guild_id": "1", "channel_id": "2"}


def test_parse_dispatch_message_create() -> None:
    event = parse_dispatch(
        EventName.MESSAGE_CREATE,
        message_json(id="1", channel_id="2", author=user_json(username="bot"), content="hi", timestamp="t"),
    )
    assert isinstance(event, Message)
    assert event.content == "hi"
    assert event.author.username == "bot"


def test_parse_dispatch_guild_create() -> None:
    event = parse_dispatch(EventName.GUILD_CREATE, GUILD_JSON)
    assert isinstance(event, GuildCreate)
    assert event.name == "My Guild"
    assert event.channels == []


def test_parse_dispatch_guild_create_types_its_channels() -> None:
    event = parse_dispatch(
        EventName.GUILD_CREATE,
        {**GUILD_JSON, "member_count": 3, "channels": [{"id": "5", "type": 0, "name": "general", "guild_id": "1"}]},
    )
    assert isinstance(event, GuildCreate)
    assert event.member_count == 3
    assert event.channels[0].name == "general"


def test_parse_dispatch_accepts_plain_str_matching_an_event_name() -> None:
    """Gateway.listen() only ever has a plain ``str`` off the socket, not an EventName member."""
    event = parse_dispatch(
        "MESSAGE_CREATE",
        message_json(id="1", channel_id="2", author=user_json(username="bot"), content="hi", timestamp="t"),
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
                "d": message_json(id="1", channel_id="2", author=user_json(username="bot"), content="hi", timestamp="t"),
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


async def test_a_payload_that_no_longer_fits_its_model_is_dispatched_raw() -> None:
    """Discord sending something the model refuses must not end the connection."""
    gateway = Gateway("token")
    bad = {"channel_id": "2"}  # TYPING_START without its required user_id and timestamp
    gateway._ws = FakeWebSocket(
        [
            {"op": Opcode.DISPATCH, "s": 1, "t": "TYPING_START", "d": bad},
            {"op": Opcode.DISPATCH, "s": 2, "t": "SOMETHING_UNMODELED", "d": {"foo": "bar"}},
        ],
    )
    received: list[tuple[str, Any]] = []

    async def dispatch(name: str, payload: Any) -> None:  # noqa: ANN401
        received.append((name, payload))

    with pytest.raises(_EndOfFrames):
        await gateway.listen(dispatch)

    assert [name for name, _ in received] == ["TYPING_START", "SOMETHING_UNMODELED"]
    raw = received[0][1]
    assert isinstance(raw, RawEvent)
    assert raw.data == bad


async def test_a_large_guild_gets_its_members_requested_with_the_members_intent() -> None:
    gateway = Gateway("token", intents=Intents.GUILD_MEMBERS)
    socket = FakeWebSocket([{"op": Opcode.DISPATCH, "s": 1, "t": "GUILD_CREATE", "d": {**GUILD_JSON, "large": True}}])
    gateway._ws = socket

    async def dispatch(_name: str, _payload: Any) -> None:  # noqa: ANN401
        return None

    with pytest.raises(_EndOfFrames):
        await gateway.listen(dispatch)

    (sent,) = [json.loads(frame) for frame in socket.sent]
    assert sent["op"] == Opcode.REQUEST_GUILD_MEMBERS
    assert sent["d"] == {"guild_id": "1", "query": "", "limit": 0, "presences": False, "nonce": "all-members"}


async def test_without_the_members_intent_nothing_is_requested() -> None:
    gateway = Gateway("token", intents=Intents.none())
    socket = FakeWebSocket([{"op": Opcode.DISPATCH, "s": 1, "t": "GUILD_CREATE", "d": {**GUILD_JSON, "large": True}}])
    gateway._ws = socket

    async def dispatch(_name: str, _payload: Any) -> None:  # noqa: ANN401
        return None

    with pytest.raises(_EndOfFrames):
        await gateway.listen(dispatch)

    assert socket.sent == []


async def test_listen_dispatches_ready_first() -> None:
    gateway = Gateway("token")
    gateway.ready = parse_ready(
        {"session_id": "s", "resume_gateway_url": "wss://x", "user": user_json(id="1", username="bot")},
    )
    gateway._ws = FakeWebSocket([{"op": Opcode.DISPATCH, "s": 1, "t": "SOMETHING_UNMODELED", "d": {}}])  # noqa: SLF001 - test wiring

    received: list[str] = []

    async def dispatch(name: str, payload: Any) -> None:  # noqa: ANN401, ARG001
        received.append(name)

    with pytest.raises(_EndOfFrames):
        await gateway.listen(dispatch)

    assert received == ["READY", "SOMETHING_UNMODELED"]


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
