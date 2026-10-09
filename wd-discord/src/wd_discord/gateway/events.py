"""Typed gateway dispatch event payloads and the DiscordModel each event's name resolves to.

Discord's gateway sends DISPATCH frames (op 0) carrying an event name (``t``) and a JSON
payload (``d``). This module holds the typed :class:`DiscordModel` payloads (mirroring the
parsing style already used by :func:`~wd_discord.gateway.connection.parse_ready` and
:func:`~wd_discord.gateway.sharding.parse_gateway_bot`) plus :class:`EventName`, which resolves
an event name to its model. The actual runtime resolution function,
:func:`~wd_discord.gateway.dispatch.parse_dispatch`, lives in its own module -
:mod:`wd_discord.gateway.dispatch` - paired with a *generated* ``dispatch.pyi`` (see
``wd-discord/scripts/generate_dispatch_overloads.py``) holding its ``@overload`` signatures.
That split exists because a stub file shadows its paired ``.py`` module entirely for type
checkers, so mixing "the real implementation" and "~75 generated overload declarations" in one
file would mean either hand-maintaining the overloads (what the generator exists to avoid) or
letting generated content live next to hand-written runtime logic in the same file.

:class:`EventName` covers every dispatch event Discord currently defines. Each member carries its own
:class:`DiscordModel` subclass as a real attribute (``EventName.MESSAGE_CREATE.model is Message``) via the
"data-carrying enum" pattern (a custom ``__new__``), so the name and its model live in exactly one place - but
only ``READY``/``MESSAGE_CREATE``/``GUILD_CREATE``/``INTERACTION_CREATE``/``VOICE_STATE_UPDATE`` have a real model
wired up so far;
every other member's ``model`` is ``None`` (dispatches as :class:`RawEvent`) until its
payload/model classes get built
(add them here, then run the generator - see its own docstring for the naming convention it
expects).

These are data only; :func:`wd_discord.entities.events.bind` wraps them in the client-bound entities a
listener receives.

``User``/``Snowflake``/``Mapping`` are imported eagerly (not via ``lazy from``) because pydantic
resolves model field annotations to real classes at class-definition time; a still-unresolved
lazy-import proxy fails schema generation (``PydanticSchemaGenerationError``).
"""

from __future__ import annotations

from collections.abc import Mapping
lazy from enum import IntEnum, StrEnum
lazy from typing import NotRequired, Self, TypedDict, cast

lazy from pydantic import Field, ModelWrapValidatorHandler, model_validator

from wd_discord.components import ComponentType
from wd_discord.interactions import ApplicationIntegrationType, InteractionContextType, Locale
from wd_discord.models import DiscordModel
from wd_discord.permissions import PermissionsField
from wd_discord.resources.channel.channel import Channel
from wd_discord.resources.entitlement import Entitlement
from wd_discord.resources.guild.guild import Guild
from wd_discord.resources.guild.member import GuildMember
from wd_discord.resources.guild.partial_guild import PartialGuild
from wd_discord.resources.guild.role import Role
from wd_discord.resources.user import User
from wd_discord.resources.voice import VoiceState
from wd_discord.snowflake import Snowflake


class RawEvent(DiscordModel):
    """Fallback for any dispatch event without a dedicated model."""

    name: str
    data: Mapping[str, object]


class UnavailableGuild(DiscordModel):
    """A guild that is offline or not sent yet (https://docs.discord.com/developers/resources/guild#unavailable-guild-object)."""

    id: Snowflake
    unavailable: bool | None = None


class Ready(DiscordModel):
    """READY (https://docs.discord.com/developers/events/gateway-events#ready).

    Parsed by :func:`~wd_discord.gateway.connection.parse_ready`.
    """

    v: int
    user: User
    guilds: list[UnavailableGuild] = Field(default_factory=list[UnavailableGuild])
    """The bot's guilds; each one arrives in full later as a GUILD_CREATE."""
    session_id: str
    resume_gateway_url: str
    shard: tuple[int, int] | None = None
    application_id: str | None = None


class GuildCreate(Guild):
    """GUILD_CREATE (https://docs.discord.com/developers/events/gateway-events#guild-create).

    A full :class:`~wd_discord.resources.guild.Guild` plus the fields only the gateway sends. ``presences`` stays
    untyped until its model exists; ``stage_instances``, ``guild_scheduled_events`` and ``soundboard_sounds`` are not
    modeled yet.
    """

    joined_at: str | None = None
    large: bool | None = None
    unavailable: bool | None = None
    member_count: int | None = None
    channels: list[Channel] = Field(default_factory=list[Channel])
    threads: list[Channel] = Field(default_factory=list[Channel])
    members: list[GuildMember] = Field(default_factory=list[GuildMember])
    voice_states: list[VoiceState] = Field(default_factory=list[VoiceState])
    """Who is in which voice channel when the guild arrives; these leave out ``guild_id``."""
    presences: list[Mapping[str, object]] = Field(default_factory=list[Mapping[str, object]])


class VoiceStateUpdate(VoiceState):
    """VOICE_STATE_UPDATE (https://docs.discord.com/developers/events/gateway-events#voice-state-update).

    Someone joined, left or moved between voice channels, or changed their mute/deafen state.
    """


class InteractionType(IntEnum):
    """The kind of interaction an INTERACTION_CREATE dispatch carries."""

    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5


class ResolvedData(DiscordModel):
    """The ``resolved`` block of interaction command data - full objects for referenced IDs.

    ``members`` (partial members, without ``user``, ``deaf`` and ``mute``) and ``messages``/``attachments`` aren't
    modeled yet.
    """

    users: dict[str, User] | None = None
    roles: dict[str, Role] | None = None
    channels: dict[str, Channel] | None = None
    """Partial channels: ``id``, ``name``, ``type``, ``permissions`` and, for threads, ``parent_id``/``thread_metadata``."""


class InteractionDataOption(DiscordModel):
    """One option value as submitted in an interaction (not the command's *definition* - see CommandOption for that)."""

    name: str
    type: int
    value: str | int | float | bool | None = None
    options: list[InteractionDataOption] | None = None
    """The chosen subcommand's own option values (only on SUB_COMMAND / SUB_COMMAND_GROUP options)."""
    focused: bool | None = None


class InteractionData(DiscordModel):
    """The ``data`` block of an application-command INTERACTION_CREATE."""

    id: Snowflake
    name: str
    type: int
    options: list[InteractionDataOption] = Field(default_factory=list[InteractionDataOption])
    resolved: ResolvedData | None = None


class MessageComponentData(DiscordModel):
    """The ``data`` block of a MESSAGE_COMPONENT INTERACTION_CREATE (a button click or select choice)."""

    custom_id: str
    component_type: ComponentType
    id: int | None = None
    """The component's numeric identifier within its message."""
    values: list[str] | None = None
    """The chosen values; only sent for select menus."""


class Interaction(DiscordModel):
    """INTERACTION_CREATE (https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object).

    The fields every interaction shares. Its ``data`` shape depends on ``type``, so each type gets a subclass
    with a precise ``data``: :meth:`model_validate` on this base returns the subclass matching ``type``, so a
    parsed interaction narrows with ``isinstance``. Build a specific interaction through its subclass; calling
    ``Interaction(...)`` directly can't swap in the subclass.
    """

    id: Snowflake
    application_id: Snowflake
    type: InteractionType
    guild_id: Snowflake | None = None
    channel_id: Snowflake | None = None
    member: GuildMember | None = None
    """The invoking member, when invoked in a guild."""
    user: User | None = None
    """The invoking user, when invoked in a DM."""
    token: str
    version: int
    app_permissions: PermissionsField | None = None
    """Permissions the app has where the interaction was sent, including overwrites."""
    locale: Locale | None = None
    """The invoking user's selected language; sent on every interaction except PING."""
    guild_locale: Locale | None = None
    """The guild's preferred locale, when invoked in a guild."""
    entitlements: list[Entitlement] | None = None
    """For monetized apps: the invoking user's (and guild's) entitlements."""
    authorizing_integration_owners: dict[ApplicationIntegrationType, Snowflake] | None = None
    """Who installed the app for this interaction, per installation context: a guild ID, a user ID, or ``0``."""
    context: InteractionContextType | None = None
    """Where the interaction was triggered from."""
    attachment_size_limit: int | None = None
    """Attachment size limit in bytes."""
    guild: PartialGuild | None = None
    """The guild the interaction was sent from."""
    channel: Channel | None = None
    """The (partial) channel the interaction was sent from."""

    @model_validator(mode="wrap")
    @classmethod
    def _parse_as_subclass(cls, data: object, handler: ModelWrapValidatorHandler[Interaction]) -> Interaction:
        """Validate a raw interaction on the base class into the subclass its ``type`` names."""
        if cls is not Interaction or not isinstance(data, Mapping):
            return handler(data)
        payload = cast("Mapping[str, object]", data)
        subclass = _INTERACTION_SUBCLASSES.get(payload.get("type"), UnknownInteraction)
        return subclass.model_validate(payload)

    @property
    def invoking_user(self) -> User | None:
        """The user who triggered this interaction, whether invoked in a guild (``member``) or a DM (``user``)."""
        if self.user is not None:
            return self.user
        return self.member.user if self.member is not None else None


class CommandInteraction(Interaction):
    """An APPLICATION_COMMAND interaction: someone ran a command."""

    data: InteractionData


class AutocompleteInteraction(Interaction):
    """An APPLICATION_COMMAND_AUTOCOMPLETE interaction: someone is typing a value for an autocomplete option."""

    data: InteractionData


class ComponentInteraction(Interaction):
    """A MESSAGE_COMPONENT interaction: someone clicked a button or chose from a select menu."""

    data: MessageComponentData
    message: dict[str, object]
    """The message the component is attached to."""


class UnknownInteraction(Interaction):
    """An interaction type without its own subclass yet (PING, MODAL_SUBMIT); ``data`` stays untyped."""

    data: Mapping[str, object] | None = None


_INTERACTION_SUBCLASSES: dict[object, type[Interaction]] = {
    InteractionType.APPLICATION_COMMAND: CommandInteraction,
    InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE: AutocompleteInteraction,
    InteractionType.MESSAGE_COMPONENT: ComponentInteraction,
}
"""The subclass each interaction type parses into; IntEnum members hash like the wire ints."""


class Message(DiscordModel):
    """MESSAGE_CREATE (subset - https://docs.discord.com/developers/resources/message)."""

    id: Snowflake
    channel_id: Snowflake
    guild_id: Snowflake | None = None
    author: User
    content: str
    timestamp: str
    edited_timestamp: str | None = None
    tts: bool
    mention_everyone: bool
    # TODO(Phase 2): mentions[]/attachments[]/embeds[]/reactions[] need their own models.


class MessageCreatePayload(TypedDict):
    """The raw ``d`` payload of a MESSAGE_CREATE dispatch, as delivered by the gateway (subset).

    Mirrors :class:`Message`'s fields; kept as a separate TypedDict (rather than typing
    :func:`~wd_discord.gateway.dispatch.parse_dispatch`'s ``data`` param directly off the
    pydantic model) so callers get a plain-dict shape to construct without needing pydantic, and
    so the wire shape and the parsed model can diverge (e.g. ``author`` here is the raw nested
    user object, not a ``User``).
    """

    id: str
    channel_id: str
    guild_id: NotRequired[str]
    author: Mapping[str, object]
    content: str
    timestamp: str
    edited_timestamp: NotRequired[str | None]
    tts: bool
    mention_everyone: bool


class ReadyPayload(TypedDict):
    """The raw ``d`` payload of a READY dispatch, as delivered by the gateway (subset)."""

    v: int
    user: Mapping[str, object]
    guilds: list[Mapping[str, object]]
    session_id: str
    resume_gateway_url: str
    shard: NotRequired[list[int]]
    application: NotRequired[Mapping[str, object]]


class GuildCreatePayload(TypedDict):
    """The raw ``d`` payload of a GUILD_CREATE dispatch, as delivered by the gateway (subset of the guild fields)."""

    id: str
    name: str
    icon: str | None
    owner_id: str
    afk_timeout: int
    roles: list[Mapping[str, object]]
    emojis: list[Mapping[str, object]]
    features: list[str]
    joined_at: NotRequired[str]
    large: NotRequired[bool]
    unavailable: NotRequired[bool]
    member_count: NotRequired[int]
    channels: NotRequired[list[Mapping[str, object]]]
    threads: NotRequired[list[Mapping[str, object]]]
    members: NotRequired[list[Mapping[str, object]]]
    voice_states: NotRequired[list[Mapping[str, object]]]
    presences: NotRequired[list[Mapping[str, object]]]


class VoiceStateUpdatePayload(TypedDict):
    """The raw ``d`` payload of a VOICE_STATE_UPDATE dispatch, as delivered by the gateway."""

    guild_id: NotRequired[str]
    channel_id: str | None
    user_id: str
    member: NotRequired[Mapping[str, object]]
    session_id: str
    deaf: bool
    mute: bool
    self_deaf: bool
    self_mute: bool
    self_stream: NotRequired[bool]
    self_video: bool
    suppress: bool
    request_to_speak_timestamp: str | None


class InteractionCreatePayload(TypedDict):
    """The raw ``d`` payload of an INTERACTION_CREATE dispatch, as delivered by the gateway (subset)."""

    id: str
    application_id: str
    type: int
    data: NotRequired[Mapping[str, object]]
    guild_id: NotRequired[str]
    channel_id: NotRequired[str]
    member: NotRequired[Mapping[str, object]]
    user: NotRequired[Mapping[str, object]]
    token: str
    version: int


class EventName(StrEnum):
    """Every dispatch event name Discord currently defines.

    READY arrives once per connection. :meth:`~wd_discord.gateway.connection.Gateway.connect` parses it with
    :func:`~wd_discord.gateway.connection.parse_ready` (never :func:`~wd_discord.gateway.dispatch.parse_dispatch`),
    and :meth:`~wd_discord.gateway.connection.Gateway.listen` then hands it to listeners like any other event.

    Each member carries its own :class:`DiscordModel` subclass as a real attribute
    (``EventName.MESSAGE_CREATE.model is Message``) via a custom ``__new__``, so the name and its
    model live in exactly one place - but most members' ``model`` is still ``None``; those
    dispatch as :class:`RawEvent` until their model gets built (see the module docstring).
    """

    model: type[DiscordModel] | None

    def __new__(cls, value: str, model: type[DiscordModel] | None = None) -> Self:
        """Build a member, attaching its ``model`` (if any) alongside the usual str ``value``."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.model = model
        return member

    READY = ("READY", Ready)
    MESSAGE_CREATE = ("MESSAGE_CREATE", Message)
    GUILD_CREATE = ("GUILD_CREATE", GuildCreate)
    INTERACTION_CREATE = ("INTERACTION_CREATE", Interaction)

    RESUMED = "RESUMED"

    APPLICATION_COMMAND_PERMISSIONS_UPDATE = "APPLICATION_COMMAND_PERMISSIONS_UPDATE"

    AUTO_MODERATION_RULE_CREATE = "AUTO_MODERATION_RULE_CREATE"
    AUTO_MODERATION_RULE_UPDATE = "AUTO_MODERATION_RULE_UPDATE"
    AUTO_MODERATION_RULE_DELETE = "AUTO_MODERATION_RULE_DELETE"
    AUTO_MODERATION_ACTION_EXECUTION = "AUTO_MODERATION_ACTION_EXECUTION"

    CHANNEL_CREATE = "CHANNEL_CREATE"
    CHANNEL_UPDATE = "CHANNEL_UPDATE"
    CHANNEL_DELETE = "CHANNEL_DELETE"
    CHANNEL_PINS_UPDATE = "CHANNEL_PINS_UPDATE"

    THREAD_CREATE = "THREAD_CREATE"
    THREAD_UPDATE = "THREAD_UPDATE"
    THREAD_DELETE = "THREAD_DELETE"
    THREAD_LIST_SYNC = "THREAD_LIST_SYNC"
    THREAD_MEMBER_UPDATE = "THREAD_MEMBER_UPDATE"
    THREAD_MEMBERS_UPDATE = "THREAD_MEMBERS_UPDATE"

    ENTITLEMENT_CREATE = "ENTITLEMENT_CREATE"
    ENTITLEMENT_UPDATE = "ENTITLEMENT_UPDATE"
    ENTITLEMENT_DELETE = "ENTITLEMENT_DELETE"

    GUILD_UPDATE = "GUILD_UPDATE"
    GUILD_DELETE = "GUILD_DELETE"
    GUILD_AUDIT_LOG_ENTRY_CREATE = "GUILD_AUDIT_LOG_ENTRY_CREATE"
    GUILD_BAN_ADD = "GUILD_BAN_ADD"
    GUILD_BAN_REMOVE = "GUILD_BAN_REMOVE"
    GUILD_EMOJIS_UPDATE = "GUILD_EMOJIS_UPDATE"
    GUILD_STICKERS_UPDATE = "GUILD_STICKERS_UPDATE"
    GUILD_INTEGRATIONS_UPDATE = "GUILD_INTEGRATIONS_UPDATE"
    GUILD_MEMBER_ADD = "GUILD_MEMBER_ADD"
    GUILD_MEMBER_REMOVE = "GUILD_MEMBER_REMOVE"
    GUILD_MEMBER_UPDATE = "GUILD_MEMBER_UPDATE"
    GUILD_MEMBERS_CHUNK = "GUILD_MEMBERS_CHUNK"
    GUILD_ROLE_CREATE = "GUILD_ROLE_CREATE"
    GUILD_ROLE_UPDATE = "GUILD_ROLE_UPDATE"
    GUILD_ROLE_DELETE = "GUILD_ROLE_DELETE"
    GUILD_SCHEDULED_EVENT_CREATE = "GUILD_SCHEDULED_EVENT_CREATE"
    GUILD_SCHEDULED_EVENT_UPDATE = "GUILD_SCHEDULED_EVENT_UPDATE"
    GUILD_SCHEDULED_EVENT_DELETE = "GUILD_SCHEDULED_EVENT_DELETE"
    GUILD_SCHEDULED_EVENT_USER_ADD = "GUILD_SCHEDULED_EVENT_USER_ADD"
    GUILD_SCHEDULED_EVENT_USER_REMOVE = "GUILD_SCHEDULED_EVENT_USER_REMOVE"
    GUILD_SOUNDBOARD_SOUND_CREATE = "GUILD_SOUNDBOARD_SOUND_CREATE"
    GUILD_SOUNDBOARD_SOUND_UPDATE = "GUILD_SOUNDBOARD_SOUND_UPDATE"
    GUILD_SOUNDBOARD_SOUND_DELETE = "GUILD_SOUNDBOARD_SOUND_DELETE"
    GUILD_SOUNDBOARD_SOUNDS_UPDATE = "GUILD_SOUNDBOARD_SOUNDS_UPDATE"

    SOUNDBOARD_SOUNDS = "SOUNDBOARD_SOUNDS"

    INTEGRATION_CREATE = "INTEGRATION_CREATE"
    INTEGRATION_UPDATE = "INTEGRATION_UPDATE"
    INTEGRATION_DELETE = "INTEGRATION_DELETE"

    INVITE_CREATE = "INVITE_CREATE"
    INVITE_DELETE = "INVITE_DELETE"

    MESSAGE_UPDATE = "MESSAGE_UPDATE"
    MESSAGE_DELETE = "MESSAGE_DELETE"
    MESSAGE_DELETE_BULK = "MESSAGE_DELETE_BULK"
    MESSAGE_REACTION_ADD = "MESSAGE_REACTION_ADD"
    MESSAGE_REACTION_REMOVE = "MESSAGE_REACTION_REMOVE"
    MESSAGE_REACTION_REMOVE_ALL = "MESSAGE_REACTION_REMOVE_ALL"
    MESSAGE_REACTION_REMOVE_EMOJI = "MESSAGE_REACTION_REMOVE_EMOJI"
    MESSAGE_POLL_VOTE_ADD = "MESSAGE_POLL_VOTE_ADD"
    MESSAGE_POLL_VOTE_REMOVE = "MESSAGE_POLL_VOTE_REMOVE"

    PRESENCE_UPDATE = "PRESENCE_UPDATE"

    STAGE_INSTANCE_CREATE = "STAGE_INSTANCE_CREATE"
    STAGE_INSTANCE_UPDATE = "STAGE_INSTANCE_UPDATE"
    STAGE_INSTANCE_DELETE = "STAGE_INSTANCE_DELETE"

    SUBSCRIPTION_CREATE = "SUBSCRIPTION_CREATE"
    SUBSCRIPTION_UPDATE = "SUBSCRIPTION_UPDATE"
    SUBSCRIPTION_DELETE = "SUBSCRIPTION_DELETE"

    TYPING_START = "TYPING_START"

    USER_UPDATE = "USER_UPDATE"

    VOICE_CHANNEL_EFFECT_SEND = "VOICE_CHANNEL_EFFECT_SEND"
    VOICE_STATE_UPDATE = ("VOICE_STATE_UPDATE", VoiceStateUpdate)
    VOICE_SERVER_UPDATE = "VOICE_SERVER_UPDATE"

    WEBHOOKS_UPDATE = "WEBHOOKS_UPDATE"
