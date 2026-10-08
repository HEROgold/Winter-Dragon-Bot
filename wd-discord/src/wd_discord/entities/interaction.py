"""Interactions bound to the client that answers them.

https://docs.discord.com/developers/interactions/receiving-and-responding

The data models in :mod:`wd_discord.gateway.events` describe what Discord sent; the classes here wrap one and
add the responses (``respond``, ``defer``, ``edit_original``, ...). :func:`wd_discord.entities.events.bind` picks
the class matching the model, so a bound interaction narrows with ``isinstance`` or ``match`` like its model does.

Discord expects an initial response within 3 seconds. The token stays valid for 15 minutes after that, for
editing the original response and sending follow-ups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
lazy from typing import TYPE_CHECKING

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import Entity, no_content
lazy from wd_discord.entities.channel import PartialChannel
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.message import Message
lazy from wd_discord.entities.user import User
lazy from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
lazy from wd_discord.gateway.events import CommandInteraction as CommandInteractionModel
lazy from wd_discord.gateway.events import ComponentInteraction as ComponentInteractionModel
lazy from wd_discord.gateway.events import Interaction as InteractionModel
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.responses import InteractionCallbackType, MessageFlags, message_data


if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from wd_core.client import JsonPayload

    from wd_discord.client import NetworkError
    from wd_discord.components import ActionRow, ComponentType
    from wd_discord.embed import Embed
    from wd_discord.gateway.events import InteractionDataOption, InteractionType, ResolvedData
    from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType, Locale
    from wd_discord.permissions import Permissions
    from wd_discord.resources.guild import GuildMember
    from wd_discord.responses import MessageData
    from wd_discord.snowflake import Snowflake


type AnyInteraction = CommandInteraction | ComponentInteraction | AutocompleteInteraction | UnknownInteraction
"""Every bound interaction :func:`~wd_discord.entities.events.bind` can return; ``match`` on it to handle each type."""


@dataclass
class ResponseState:
    """Whether an interaction already got its one initial response."""

    responded: bool = False


@dataclass(frozen=True)
class Interaction[M: InteractionModel](Entity[M]):
    """The fields and responses every interaction shares."""

    _state: ResponseState = field(default_factory=ResponseState, init=False, repr=False, compare=False)

    @property
    def id(self) -> Snowflake:
        """The interaction's ID."""
        return self.model.id

    @property
    def type(self) -> InteractionType:
        """The kind of interaction."""
        return self.model.type

    @property
    def token(self) -> str:
        """The token for responding; valid for 15 minutes."""
        return self.model.token

    @property
    def application_id(self) -> Snowflake:
        """The ID of the application the interaction is for."""
        return self.model.application_id

    @property
    def user(self) -> User | None:
        """Who triggered the interaction, whether in a guild or a DM."""
        user = self.model.invoking_user
        return None if user is None else User(self.client, user)

    @property
    def member(self) -> GuildMember | None:
        """The invoking guild member, when invoked in a guild."""
        return self.model.member

    @property
    def guild(self) -> PartialGuild | None:
        """The guild the interaction was sent from, if any."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def channel(self) -> PartialChannel | None:
        """The channel the interaction was sent from, if any."""
        channel_id = self.model.channel_id
        return None if channel_id is None else PartialChannel(self.client, channel_id)

    @property
    def locale(self) -> Locale | None:
        """The invoking user's language."""
        return self.model.locale

    @property
    def guild_locale(self) -> Locale | None:
        """The guild's preferred language, when invoked in a guild."""
        return self.model.guild_locale

    @property
    def app_permissions(self) -> Permissions | None:
        """What the app may do where the interaction was sent."""
        return self.model.app_permissions

    @property
    def context(self) -> InteractionContextType | None:
        """Where the interaction was triggered from."""
        return self.model.context

    @property
    def responded(self) -> bool:
        """Whether the interaction already got its initial response."""
        return self._state.responded

    @property
    def _webhook_path(self) -> str:
        return f"/webhooks/{self.application_id}/{self.token}"

    async def _callback(
        self,
        callback_type: InteractionCallbackType,
        data: MessageData | None = None,
    ) -> NetworkError | None:
        """POST /interactions/{id}/{token}/callback - send the initial response, remembering that it was sent."""
        payload: JsonPayload = {"type": callback_type}
        if data:
            payload["data"] = data
        error = no_content(await self.client.post(f"/interactions/{self.id}/{self.token}/callback", json=payload))
        if error is None:
            self._state.responded = True
        return error

    async def respond(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
        ephemeral: bool = False,
    ) -> NetworkError | None:
        """Reply with a message; ``ephemeral`` shows it only to the invoking user.

        Once the interaction was answered (or deferred), the reply is sent as a follow-up instead, which
        replaces the loading state of a deferred response.
        """
        if self.responded:
            message = await self.followup(content, embeds=embeds, components=components, ephemeral=ephemeral)
            return message if is_network_error(message) else None
        flags = MessageFlags.EPHEMERAL if ephemeral else None
        data = message_data(content=content, embeds=embeds, components=components, flags=flags)
        return await self._callback(InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE, data)

    async def defer(self, *, ephemeral: bool = False) -> NetworkError | None:
        """Acknowledge now and show a loading state; does nothing when already answered.

        Finish with :meth:`edit_original` or :meth:`respond` within 15 minutes. ``ephemeral`` decides whether
        that eventual response is visible only to the invoking user.
        """
        if self.responded:
            return None
        data = message_data(flags=MessageFlags.EPHEMERAL) if ephemeral else None
        return await self._callback(InteractionCallbackType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE, data)

    async def edit_original(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
    ) -> Message | NetworkError:
        """PATCH /webhooks/{application_id}/{token}/messages/@original - edit the initial response.

        A ``None`` argument leaves that part of the message unchanged; an empty sequence clears it.
        """
        payload = message_data(content=content, embeds=embeds, components=components)
        result = await self.client.patch(f"{self._webhook_path}/messages/@original", json=payload)
        return self._entity(result, MessageModel, Message)

    async def delete_original(self) -> NetworkError | None:
        """DELETE /webhooks/{application_id}/{token}/messages/@original - remove the initial response."""
        return no_content(await self.client.delete(f"{self._webhook_path}/messages/@original", json={}))

    async def followup(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
        ephemeral: bool = False,
    ) -> Message | NetworkError:
        """POST /webhooks/{application_id}/{token} - send another message after the initial response."""
        flags = MessageFlags.EPHEMERAL if ephemeral else None
        payload = message_data(content=content, embeds=embeds, components=components, flags=flags)
        return self._entity(await self.client.post(self._webhook_path, json=payload), MessageModel, Message)


class CommandInteraction(Interaction[CommandInteractionModel]):
    """Someone ran an application command."""

    @property
    def command_id(self) -> Snowflake:
        """The ID of the command that ran."""
        return self.model.data.id

    @property
    def command_name(self) -> str:
        """The name of the command that ran."""
        return self.model.data.name

    @property
    def options(self) -> list[InteractionDataOption]:
        """The submitted option values; a subcommand's own values are nested in its option."""
        return self.model.data.options

    @property
    def resolved(self) -> ResolvedData | None:
        """Full objects for the IDs referenced by option values."""
        return self.model.data.resolved


class ComponentInteraction(Interaction[ComponentInteractionModel]):
    """Someone clicked a button or chose from a select menu."""

    @property
    def custom_id(self) -> str:
        """The ``custom_id`` of the component that was used."""
        return self.model.data.custom_id

    @property
    def component_type(self) -> ComponentType:
        """The kind of component that was used."""
        return self.model.data.component_type

    @property
    def values(self) -> list[str]:
        """The chosen values of a select menu; empty for buttons."""
        return self.model.data.values or []

    @property
    def message(self) -> Mapping[str, object]:
        """The message the component is attached to, as sent."""
        return self.model.message

    async def update(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
    ) -> NetworkError | None:
        """Edit the component's message as the initial response.

        A ``None`` argument leaves that part of the message unchanged. Once the interaction was answered,
        edits the original response instead.
        """
        if self.responded:
            message = await self.edit_original(content, embeds=embeds, components=components)
            return message if is_network_error(message) else None
        data = message_data(content=content, embeds=embeds, components=components)
        return await self._callback(InteractionCallbackType.UPDATE_MESSAGE, data)

    async def defer_update(self) -> NetworkError | None:
        """Acknowledge now, without a loading state, and edit the component's message later; no-op once answered."""
        if self.responded:
            return None
        return await self._callback(InteractionCallbackType.DEFERRED_UPDATE_MESSAGE)


class AutocompleteInteraction(Interaction[AutocompleteInteractionModel]):
    """Someone is typing a value for an autocomplete option."""

    @property
    def command_name(self) -> str:
        """The name of the command being filled in."""
        return self.model.data.name

    @property
    def options(self) -> list[InteractionDataOption]:
        """The option values typed so far; the one being typed has ``focused`` set."""
        return self.model.data.options

    async def suggest(self, choices: Sequence[ApplicationCommandOptionChoice]) -> NetworkError | None:
        """Offer ``choices`` (at most 25) for the focused option."""
        data: MessageData = {"choices": [choice.model_dump(mode="json", exclude_none=True) for choice in choices]}
        return await self._callback(InteractionCallbackType.APPLICATION_COMMAND_AUTOCOMPLETE_RESULT, data)


class UnknownInteraction(Interaction[InteractionModel]):
    """An interaction type without its own class yet (PING, MODAL_SUBMIT)."""
