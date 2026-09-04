"""Unit tests: gateway presence (object -> API) and READY (API -> object) helpers."""
from __future__ import annotations

lazy from wd_discord.gateway import GatewayActivity, Status, build_presence, parse_ready
lazy from wd_errors import Activity


def test_activity_to_dict_minimal() -> None:
    assert GatewayActivity("Hello", Activity.PLAYING).to_dict() == {"name": "Hello", "type": 0}


def test_activity_to_dict_with_extras() -> None:
    activity = GatewayActivity("watching", Activity.CUSTOM, url="https://x", state="hi")
    assert activity.to_dict() == {"name": "watching", "type": 4, "url": "https://x", "state": "hi"}


def test_build_presence_shape() -> None:
    presence = build_presence([GatewayActivity("a game", Activity.PLAYING)], Status.dnd)
    assert presence == {
        "since": None,
        "activities": [{"name": "a game", "type": 0}],
        "status": "dnd",
        "afk": False,
    }


def test_build_presence_accepts_str_status() -> None:
    assert build_presence([], "idle")["status"] == "idle"


def test_status_values() -> None:
    assert Status.online == "online"
    assert Status.invisible == "invisible"


def test_parse_ready_with_dispatch_wrapper() -> None:
    payload = {
        "t": "READY",
        "op": 0,
        "d": {
            "session_id": "abc123",
            "resume_gateway_url": "wss://resume.example",
            "user": {"id": "42", "username": "bot"},
            "application": {"id": "99"},
        },
    }
    ready = parse_ready(payload)
    assert ready.session_id == "abc123"
    assert ready.resume_gateway_url == "wss://resume.example"
    assert ready.user["id"] == "42"
    assert ready.application_id == "99"


def test_parse_ready_accepts_inner_dict() -> None:
    ready = parse_ready({"session_id": "s", "resume_gateway_url": "wss://x"})
    assert ready.session_id == "s"
    assert ready.application_id is None
