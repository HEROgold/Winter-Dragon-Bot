"""Unit tests: command-payload building and response parsing (no network)."""

from __future__ import annotations

from wd_discord.client import _build_command_payload
from wd_discord.interactions import ApplicationCommandOptionType, CommandOption, RegisteredCommand
from wd_discord.permissions import Permissions


def test_build_command_payload_includes_options() -> None:
    option = CommandOption(type=ApplicationCommandOptionType.USER, name="user", description="Target user", required=True)
    payload = _build_command_payload("percentage", "Calculate a percentage", [option])
    assert payload == {
        "name": "percentage",
        "description": "Calculate a percentage",
        "type": 1,
        "options": [{"type": 6, "name": "user", "description": "Target user", "required": True}],
        "default_member_permissions": None,
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


def test_build_command_payload_sends_null_default_member_permissions_when_none() -> None:
    """Unset permissions are sent as JSON null, so an edit (PATCH) clears previously-set permissions."""
    payload = _build_command_payload("ping", "Ping", [])
    assert "default_member_permissions" in payload
    assert payload["default_member_permissions"] is None


def test_build_command_payload_sends_permissions_as_decimal_string() -> None:
    payload = _build_command_payload("ping", "Ping", [], Permissions.MANAGE_GUILD)
    assert payload["default_member_permissions"] == str(int(Permissions.MANAGE_GUILD))
