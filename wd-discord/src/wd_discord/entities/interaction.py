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
lazy from wd_discord.entities.channel import Channel, PartialChannel
lazy from wd_discord.entities.entitlement import Entitlement
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.member import Member
lazy from wd_discord.entities.message import Message
lazy from wd_discord.entities.resolved import Resolved
lazy from wd_discord.entities.user import User
lazy from wd_discord.files import request_body
lazy from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
lazy from wd_discord.gateway.events import CommandInteraction as CommandInteractionModel
lazy from wd_discord.gateway.events import ComponentInteraction as ComponentInteractionModel
lazy from wd_discord.gateway.events import Interaction as InteractionModel
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.responses import InteractionCallbackType, MessageFlags, message_data


if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from string.templatelib import Template

    from wd_core.client import JsonPayload

    from wd_discord.client import Client, NetworkError
    from wd_discord.components import ActionRow, ComponentType
    from wd_discord.embed import Embed
    from wd_discord.files import File
    from wd_discord.gateway.events import InteractionDataOption, InteractionType
    from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType, Locale
    from wd_discord.permissions import Permissions
    from wd_discord.resources.channel import Channel as ChannelModel
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
    def member(self) -> Member | None:
        """The invoking guild member, when invoked in a guild."""
        member, guild_id = self.model.member, self.model.guild_id
        if member is None or member.user is None or guild_id is None:
            return None
        return Member(self.client, member, guild_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The guild the interaction was sent from, if any."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def channel(self) -> Channel | PartialChannel | None:
        """The channel the interaction was sent from, in full when Discord sent it along (it usually does)."""
        if self.model.channel is not None:
            return _full_channel(self.client, self.model.channel, self.model.guild_id)
        channel_id = self.model.channel_id
        return None if channel_id is None else PartialChannel(self.client, channel_id)

    @property
    def entitlements(self) -> Generator[Entitlement]:
        """The invoking user's and guild's entitlements to the application's SKUs."""
        for entitlement in self.model.entitlements or []:
            yield Entitlement(self.client, entitlement)

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
    def _webhook_path(self) -> Template:
        return t"/webhooks/{self.application_id}/{self.token}"

    async def _callback(
        self,
        callback_type: InteractionCallbackType,
        data: MessageData | None = None,
        files: Sequence[File] = (),
    ) -> NetworkError | None:
        """POST /interactions/{id}/{token}/callback - send the initial response, remembering that it was sent."""
        payload: JsonPayload = {"type": callback_type}
        if data:
            payload["data"] = data
        path = t"/interactions/{self.id}/{self.token}/callback"
        error = no_content(await self.client.post(path, **request_body(payload, files)))
        if error is None:
            self._state.responded = True
        return error

    async def respond(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
        files: Sequence[File] = (),
        ephemeral: bool = False,
    ) -> NetworkError | None:
        """Reply with a message; ``ephemeral`` shows it only to the invoking user.

        Once the interaction was answered (or deferred), the reply is sent as a follow-up instead, which
        replaces the loading state of a deferred response.
        """
        if self.responded:
            message = await self.followup(content, embeds=embeds, components=components, files=files, ephemeral=ephemeral)
            return message if is_network_error(message) else None
        flags = MessageFlags.EPHEMERAL if ephemeral else None
        data = message_data(content=content, embeds=embeds, components=components, flags=flags, files=files)
        return await self._callback(InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE, data, files)

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
        files: Sequence[File] = (),
    ) -> Message | NetworkError:
        """PATCH /webhooks/{application_id}/{token}/messages/@original - edit the initial response.

        A ``None`` argument leaves that part of the message unchanged; an empty sequence clears it. ``files`` are
        added to the message's attachments.
        """
        payload = message_data(content=content, embeds=embeds, components=components, files=files)
        result = await self.client.patch(self._webhook_path + t"/messages/@original", **request_body(payload, files))
        return self._entity(result, MessageModel, Message)

    async def delete_original(self) -> NetworkError | None:
        """DELETE /webhooks/{application_id}/{token}/messages/@original - remove the initial response."""
        return no_content(await self.client.delete(self._webhook_path + t"/messages/@original", json={}))

    async def followup(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
        files: Sequence[File] = (),
        ephemeral: bool = False,
    ) -> Message | NetworkError:
        """POST /webhooks/{application_id}/{token} - send another message after the initial response."""
        flags = MessageFlags.EPHEMERAL if ephemeral else None
        payload = message_data(content=content, embeds=embeds, components=components, flags=flags, files=files)
        result = await self.client.post(self._webhook_path, **request_body(payload, files))
        return self._entity(result, MessageModel, Message)


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
    def resolved(self) -> Resolved | None:
        """Full objects for the users, roles and channels the option values name."""
        resolved = self.model.data.resolved
        return None if resolved is None else Resolved(self.client, resolved, self.model.guild_id)


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
    def message(self) -> Message:
        """The message the component is attached to."""
        return Message(self.client, MessageModel.model_validate(self.model.message))

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

    @property
    def resolved(self) -> Resolved | None:
        """Full objects for the users, roles and channels the option values typed so far name."""
        resolved = self.model.data.resolved
        return None if resolved is None else Resolved(self.client, resolved, self.model.guild_id)

    async def suggest(self, choices: Sequence[ApplicationCommandOptionChoice]) -> NetworkError | None:
        """Offer ``choices`` (at most 25) for the focused option."""
        data: MessageData = {"choices": [choice.model_dump(mode="json", exclude_none=True) for choice in choices]}
        return await self._callback(InteractionCallbackType.APPLICATION_COMMAND_AUTOCOMPLETE_RESULT, data)


class UnknownInteraction(Interaction[InteractionModel]):
    """An interaction type without its own class yet (PING, MODAL_SUBMIT)."""


def _full_channel(client: Client, channel: ChannelModel, guild_id: Snowflake | None) -> Channel:
    """Return the channel Discord sent with an interaction, given the interaction's guild when it left that out."""
    if channel.guild_id is None and guild_id is not None:
        channel = channel.model_copy(update={"guild_id": guild_id})
    return Channel(client, channel)
