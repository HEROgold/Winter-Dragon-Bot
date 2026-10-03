"""Unit tests: the Interaction dispatch-event model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wd_discord import models
from wd_discord.gateway import EventName
from wd_discord.gateway.dispatch import parse_dispatch
from wd_discord.gateway.events import Interaction, InteractionType
from wd_discord.interactions import ApplicationCommand, InteractionContextType


if TYPE_CHECKING:
    import pytest


def test_interaction_create_has_a_model() -> None:
    assert EventName.INTERACTION_CREATE.model is Interaction


def test_parse_dispatch_parses_application_command_interaction() -> None:
    payload = {
        "id": "1",
        "application_id": "2",
        "type": 2,
        "token": "tok",
        "version": 1,
        "user": {"id": "3", "username": "asker", "discriminator": "0"},
        "data": {
            "id": "10",
            "name": "percentage",
            "type": 1,
            "options": [{"name": "user", "type": 6, "value": "4"}],
            "resolved": {"users": {"4": {"id": "4", "username": "target", "discriminator": "0"}}},
        },
    }
    interaction = parse_dispatch("INTERACTION_CREATE", payload)
    assert isinstance(interaction, Interaction)
    assert interaction.type is InteractionType.APPLICATION_COMMAND
    assert interaction.data is not None
    assert interaction.data.name == "percentage"
    assert interaction.data.resolved is not None
    assert interaction.data.resolved.users is not None
    assert interaction.data.resolved.users["4"].username == "target"
    assert interaction.invoking_user is not None
    assert interaction.invoking_user.username == "asker"


def test_realistic_interaction_create_reports_no_unknown_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fields Discord sends on every interaction are declared, so none reach the unknown-field reporter."""
    reports: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(models, "_report_unknown_fields", lambda name, extra: reports.append((name, dict(extra))))
    payload = {
        "id": "1",
        "application_id": "2",
        "type": 2,
        "token": "tok",
        "version": 1,
        "guild_id": "5",
        "channel_id": "6",
        "member": {"user": {"id": "3", "username": "asker", "discriminator": "0"}, "roles": []},
        "data": {"id": "10", "name": "percentage", "type": 1},
        "app_permissions": "562949953421311",
        "locale": "en-US",
        "guild_locale": "en-US",
        "entitlements": [],
        "authorizing_integration_owners": {"0": "5"},
        "context": 0,
        "attachment_size_limit": 10485760,
        "guild": {"id": "5", "locale": "en-US", "features": []},
        "channel": {"id": "6", "type": 0, "name": "general"},
    }

    interaction = parse_dispatch("INTERACTION_CREATE", payload)

    assert isinstance(interaction, Interaction)
    assert interaction.locale == "en-US"
    assert reports == []


def test_application_command_reports_no_unknown_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """The extra keys Discord returns for a registered command are declared."""
    reports: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(models, "_report_unknown_fields", lambda name, extra: reports.append((name, dict(extra))))

    command = ApplicationCommand.model_validate(
        {
            "id": "1",
            "application_id": "2",
            "version": "3",
            "name": "ping",
            "description": "d",
            "type": 1,
            "contexts": [0, 1, 2],
            "integration_types": [0],
            "default_permission": True,
        },
    )

    assert command.contexts == list(InteractionContextType)
    assert reports == []
