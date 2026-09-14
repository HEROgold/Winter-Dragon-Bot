"""Unit tests: command-payload building and response parsing (no network)."""
from __future__ import annotations

from wd_discord.client import _build_command_payload
from wd_discord.interactions import ApplicationCommandOptionType, CommandOption, RegisteredCommand


def test_build_command_payload_includes_options() -> None:
    option = CommandOption(type=ApplicationCommandOptionType.USER, name="user", description="Target user", required=True)
    payload = _build_command_payload("percentage", "Calculate a percentage", [option])
    assert payload == {
        "name": "percentage",
        "description": "Calculate a percentage",
        "type": 1,
        "options": [{"type": 6, "name": "user", "description": "Target user", "required": True}],
    }


def test_build_command_payload_no_options() -> None:
    payload = _build_command_payload("ping", "Ping", [])
    assert payload["options"] == []


def test_registered_command_round_trips_from_create_response() -> None:
    response_json = {
        "id": "1",
        "application_id": "2",
        "version": "3",
        "name": "percentage",
        "description": "Calculate a percentage",
        "options": [],
    }
    command = RegisteredCommand.model_validate(response_json)
    assert command.name == "percentage"
