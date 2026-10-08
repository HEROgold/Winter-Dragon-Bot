"""Unit tests: the Interaction dispatch-event model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wd_discord import models
from wd_discord.components import ComponentType
from wd_discord.gateway import EventName
from wd_discord.gateway.dispatch import parse_dispatch
from wd_discord.gateway.events import (
    CommandInteraction,
    ComponentInteraction,
    Interaction,
    InteractionType,
    UnknownInteraction,
)
from wd_discord.interactions import ApplicationCommand, InteractionContextType, Locale
from wd_discord.resources.guild import GuildMember


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
        "member": {
            "user": {"id": "3", "username": "asker", "discriminator": "0"},
            "roles": [],
            "joined_at": "2024-01-01T00:00:00.000000+00:00",
            "deaf": False,
            "mute": False,
            "flags": 0,
            "permissions": "562949953421311",
        },
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

    assert isinstance(interaction, CommandInteraction)
    assert interaction.locale is Locale.ENGLISH_US
    assert interaction.context is InteractionContextType.GUILD
    assert interaction.guild is not None
    assert interaction.channel is not None
    assert interaction.member is not None
    assert interaction.member.user is not None
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


def _interaction_payload(**overrides: object) -> dict[str, object]:
    """Build a minimal INTERACTION_CREATE payload, invoked in a DM."""
    payload: dict[str, object] = {
        "id": "1",
        "application_id": "2",
        "type": 2,
        "token": "tok",
        "version": 1,
        "user": {"id": "3", "username": "asker", "discriminator": "0"},
        "data": {"id": "10", "name": "steam", "type": 1},
    }
    return payload | overrides


def test_component_interaction_parses_into_its_subclass() -> None:
    payload = _interaction_payload(
        type=3,
        data={"custom_id": "steam-show:3:100:1", "component_type": 2, "id": 4},
        message={"id": "11"},
    )

    interaction = parse_dispatch("INTERACTION_CREATE", payload)

    assert isinstance(interaction, ComponentInteraction)
    assert interaction.data.custom_id == "steam-show:3:100:1"
    assert interaction.data.component_type is ComponentType.BUTTON


def test_command_interaction_parses_into_its_subclass() -> None:
    interaction = Interaction.model_validate(_interaction_payload())
    assert isinstance(interaction, CommandInteraction)
    assert interaction.data.name == "steam"


def test_interaction_types_without_a_subclass_parse_as_unknown() -> None:
    interaction = Interaction.model_validate(_interaction_payload(type=5, data={"custom_id": "modal", "components": []}))
    assert isinstance(interaction, UnknownInteraction)
    assert interaction.data == {"custom_id": "modal", "components": []}


def test_invoking_user_comes_from_the_guild_member() -> None:
    member = {
        "user": {"id": "7", "username": "member", "discriminator": "0"},
        "roles": [],
        "joined_at": None,
        "deaf": False,
        "mute": False,
    }
    interaction = Interaction.model_validate(_interaction_payload(user=None, member=member, guild_id="5"))
    assert isinstance(interaction.member, GuildMember)
    assert interaction.invoking_user is not None
    assert interaction.invoking_user.username == "member"
