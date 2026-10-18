"""Unit tests: Gateway.run resumes or re-identifies when the connection ends, over scripted fake sockets."""

from __future__ import annotations

lazy import json
lazy from typing import Any

lazy import pytest
lazy import wd_discord.gateway.connection as connection_module
lazy from wd_discord.gateway.connection import Gateway, GatewayClosedError, Opcode
lazy from websockets.exceptions import ConnectionClosed
lazy from websockets.frames import Close


HELLO = {"op": Opcode.HELLO, "d": {"heartbeat_interval": 60_000}}
USER = {"id": "1", "username": "bot", "discriminator": "0"}
SESSION = {"session_id": "s1", "resume_gateway_url": "wss://resume", "user": USER}
READY = {"op": Opcode.DISPATCH, "s": 1, "t": "READY", "d": SESSION}
READY_2 = {**READY, "d": {**SESSION, "session_id": "s2"}}


def _event(seq: int) -> dict[str, Any]:
    return {"op": Opcode.DISPATCH, "s": seq, "t": "SOMETHING_UNMODELED", "d": {"n": seq}}


def _closed(code: int) -> ConnectionClosed:
    return ConnectionClosed(Close(code, "closed"), None)


class _EndOfScript(Exception):
    """Raised once every scripted socket is used up, to stop ``Gateway.run``."""


type Script = list[dict[str, Any] | BaseException]
"""What one socket receives, in order; an exception is raised from ``recv`` instead."""


class FakeSocket:
    """Replays scripted frames; an exception in the script is raised from ``recv`` instead."""

    def __init__(self, url: str, script: Script) -> None:
        self.url = url
        self._script = list(script)
        self.sent: list[dict[str, Any]] = []

    async def recv(self) -> str:
        if not self._script:
            raise _EndOfScript
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return json.dumps(item)

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))

    async def close(self) -> None:
        pass


@pytest.fixture
def sockets() -> list[FakeSocket]:
    """Every socket opened so far, in order; :func:`_script` decides what each one receives."""
    return []


def _script(monkeypatch: pytest.MonkeyPatch, opened: list[FakeSocket], *scripts: Script | BaseException) -> None:
    """Make the next connections return sockets playing ``scripts`` in turn; a script that's an exception fails to connect."""
    remaining = list(scripts)

    async def fake_connect(url: str) -> FakeSocket:
        if not remaining:
            raise _EndOfScript
        script = remaining.pop(0)
        if isinstance(script, BaseException):
            raise script
        socket = FakeSocket(url, script)
        opened.append(socket)
        return socket

    monkeypatch.setattr(connection_module, "connect", fake_connect)


def _gateway() -> Gateway:
    gateway = Gateway("token", url="wss://gateway/?v=10&encoding=json")
    gateway.reidentify_delay = (0.0, 0.0)
    gateway.resume_backoff = 0.0
    return gateway


async def _run(gateway: Gateway) -> list[str]:
    """Connect, run until the script ends, and return the dispatched event names (with their sequence)."""
    received: list[str] = []

    async def dispatch(name: str, payload: Any) -> None:  # noqa: ANN401
        data = getattr(payload, "data", None)
        received.append(f"{name}:{data['n']}" if isinstance(data, dict) and "n" in data else name)

    await gateway.connect()
    with pytest.raises(_EndOfScript):
        await gateway.run(dispatch)
    await gateway.close()
    return received


def _ops(socket: FakeSocket) -> list[int]:
    return [frame["op"] for frame in socket.sent if frame["op"] != Opcode.HEARTBEAT]


async def test_reconnect_request_resumes_the_session_without_a_second_ready(
    monkeypatch: pytest.MonkeyPatch,
    sockets: list[FakeSocket],
) -> None:
    _script(
        monkeypatch,
        sockets,
        [HELLO, READY, _event(2), {"op": Opcode.RECONNECT}],
        [HELLO, _event(3)],
    )

    received = await _run(_gateway())

    first, resumed = sockets
    assert _ops(first) == [Opcode.IDENTIFY]
    assert resumed.url == "wss://resume/?v=10&encoding=json"
    assert resumed.sent[-1] == {"op": Opcode.RESUME, "d": {"token": "token", "session_id": "s1", "seq": 2}}
    assert received == ["READY", "SOMETHING_UNMODELED:2", "SOMETHING_UNMODELED:3"]


async def test_resumable_invalid_session_resumes(monkeypatch: pytest.MonkeyPatch, sockets: list[FakeSocket]) -> None:
    _script(monkeypatch, sockets, [HELLO, READY, {"op": Opcode.INVALID_SESSION, "d": True}], [HELLO])

    await _run(_gateway())

    assert _ops(sockets[1]) == [Opcode.RESUME]


async def test_ended_session_identifies_again_and_dispatches_a_new_ready(
    monkeypatch: pytest.MonkeyPatch,
    sockets: list[FakeSocket],
) -> None:
    _script(monkeypatch, sockets, [HELLO, READY, {"op": Opcode.INVALID_SESSION, "d": False}], [HELLO, READY_2])

    gateway = _gateway()
    received = await _run(gateway)

    assert sockets[1].url == "wss://gateway/?v=10&encoding=json"
    assert _ops(sockets[1]) == [Opcode.IDENTIFY]
    assert gateway.ready is not None
    assert gateway.ready.session_id == "s2"
    assert received == ["READY", "READY"]


async def test_dropped_socket_resumes(monkeypatch: pytest.MonkeyPatch, sockets: list[FakeSocket]) -> None:
    _script(monkeypatch, sockets, [HELLO, READY, _closed(1006)], [HELLO])

    await _run(_gateway())

    assert _ops(sockets[1]) == [Opcode.RESUME]


@pytest.mark.parametrize("code", [4007, 4009])
async def test_close_codes_that_end_the_session_identify_again(
    monkeypatch: pytest.MonkeyPatch,
    sockets: list[FakeSocket],
    code: int,
) -> None:
    _script(monkeypatch, sockets, [HELLO, READY, _closed(code)], [HELLO, READY_2])

    await _run(_gateway())

    assert _ops(sockets[1]) == [Opcode.IDENTIFY]


async def test_fatal_close_code_raises(monkeypatch: pytest.MonkeyPatch, sockets: list[FakeSocket]) -> None:
    _script(monkeypatch, sockets, [HELLO, READY, _closed(4004)])
    gateway = _gateway()

    async def dispatch(name: str, payload: Any) -> None:  # noqa: ANN401
        pass

    await gateway.connect()
    with pytest.raises(GatewayClosedError, match="4004"):
        await gateway.run(dispatch)
    await gateway.close()


async def test_failed_resumes_fall_back_to_identifying(monkeypatch: pytest.MonkeyPatch, sockets: list[FakeSocket]) -> None:
    unreachable: list[Script | BaseException] = [OSError("unreachable")] * connection_module.MAX_RESUME_ATTEMPTS
    _script(monkeypatch, sockets, [HELLO, READY, {"op": Opcode.RECONNECT}], *unreachable, [HELLO, READY_2])

    await _run(_gateway())

    assert len(sockets) == 2
    assert _ops(sockets[1]) == [Opcode.IDENTIFY]
