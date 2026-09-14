"""Unit tests: the Interaction dispatch-event model."""
from __future__ import annotations

from wd_discord.gateway import EventName
from wd_discord.gateway.dispatch import parse_dispatch
from wd_discord.gateway.events import Interaction, InteractionType


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
