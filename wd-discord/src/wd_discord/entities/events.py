"""Gateway dispatch events bound to the client that received them.

:mod:`wd_discord.gateway.events` parses each dispatch into a data model; :func:`bind` wraps that model in
the entity a listener acts on, so ``message.channel.send(...)`` needs no client passed around. Events without
an entity yet (anything parsed as :class:`~wd_discord.gateway.events.RawEvent`) come back unchanged.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.guild import GatewayGuild
lazy from wd_discord.entities.interaction import (
    AnyInteraction,
    AutocompleteInteraction,
    CommandInteraction,
    ComponentInteraction,
    UnknownInteraction,
)
lazy from wd_discord.entities.message import Message
lazy from wd_discord.entities.ready import Ready
lazy from wd_discord.entities.voice import VoiceState
lazy from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
lazy from wd_discord.gateway.events import CommandInteraction as CommandInteractionModel
lazy from wd_discord.gateway.events import ComponentInteraction as ComponentInteractionModel
lazy from wd_discord.gateway.events import EventName, GuildCreate, VoiceStateUpdate
lazy from wd_discord.gateway.events import Interaction as InteractionModel
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.gateway.events import Ready as ReadyModel


if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import TypeAliasType

    from wd_discord.client import Client
    from wd_discord.models import DiscordModel


type BoundEvent = AnyInteraction | Message | GatewayGuild | Ready | VoiceState
"""Every entity :func:`bind` can return; ``match`` on it to handle each event."""


def bind(client: Client, model: DiscordModel) -> BoundEvent | DiscordModel:
    """Wrap a parsed dispatch ``model`` in the entity bound to ``client``, or return it as is if it has none."""
    match model:
        case InteractionModel():
            return _bind_interaction(client, model)
        case MessageModel():
            return Message(client, model)
        case GuildCreate():
            return GatewayGuild(client, model)
        case ReadyModel():
            return Ready(client, model)
        case VoiceStateUpdate():
            return VoiceState(client, model)
        case _:
            return model


def _bind_interaction(client: Client, model: InteractionModel) -> AnyInteraction:
    """Wrap an interaction ``model`` in the bound class matching its type."""
    match model:
        case CommandInteractionModel():
            return CommandInteraction(client, model)
        case ComponentInteractionModel():
            return ComponentInteraction(client, model)
        case AutocompleteInteractionModel():
            return AutocompleteInteraction(client, model)
        case _:
            return UnknownInteraction(client, model)


def event_entities() -> Mapping[EventName, type | TypeAliasType]:
    """Return the entity (or union of entities) :func:`bind` returns for each event; the source of ``listener.pyi``."""
    return {
        EventName.READY: Ready,
        EventName.MESSAGE_CREATE: Message,
        EventName.GUILD_CREATE: GatewayGuild,
        EventName.INTERACTION_CREATE: AnyInteraction,
        EventName.VOICE_STATE_UPDATE: VoiceState,
    }
