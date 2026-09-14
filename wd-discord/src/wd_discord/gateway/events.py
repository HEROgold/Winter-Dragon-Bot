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

:class:`EventName` covers every dispatch event Discord currently defines (except READY - see its
own docstring note). Each member carries its own :class:`DiscordModel` subclass as a real
attribute (``EventName.MESSAGE_CREATE.model is Message``) via the "data-carrying enum" pattern (a
custom ``__new__``), so the name and its model live in exactly one place - but only
``MESSAGE_CREATE``/``GUILD_CREATE`` have a real model wired up so far; every other member's
``model`` is ``None`` (dispatches as :class:`RawEvent`) until its payload/model classes get built
(add them here, then run the generator - see its own docstring for the naming convention it
expects).

``User``/``Snowflake``/``Mapping`` are imported eagerly (not via ``lazy from``) because pydantic
resolves model field annotations to real classes at class-definition time; a still-unresolved
lazy-import proxy fails schema generation (``PydanticSchemaGenerationError``). ``Guild``/``Channel``
have this same problem internally today (pre-existing, unrelated to this change), so
:class:`GuildCreate` intentionally does not subclass :class:`~wd_discord.resources.guild.Guild` or type its
nested collections as ``list[Channel]`` - see the TODO on :class:`GuildCreate`.
"""

from __future__ import annotations

from collections.abc import Mapping
lazy from enum import StrEnum
lazy from typing import NotRequired, Self, TypedDict

lazy from pydantic import Field

from wd_discord.models import DiscordModel
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake


class RawEvent(DiscordModel):
    """Fallback for any dispatch event without a dedicated model."""

    name: str
    data: Mapping[str, object]


class GuildCreate(DiscordModel):
    """GUILD_CREATE (subset - https://docs.discord.com/developers/events/gateway-events#guild-create).

    TODO(Phase 2): should subclass :class:`~wd_discord.resources.guild.Guild` and type ``channels`` as
    ``list[Channel]``, but ``Guild``/``Channel`` currently fail pydantic schema generation
    themselves (unresolved ``lazy import`` proxies used as nested field types) - fix that
    alongside the Interaction/CommandTree pydantic port, then merge this into ``Guild``.
    """

    id: Snowflake
    name: str
    owner_id: Snowflake
    joined_at: str | None = None
    large: bool | None = None
    unavailable: bool | None = None
    member_count: int | None = None
    channels: list[Mapping[str, object]] = Field(default_factory=list)
    members: list[Mapping[str, object]] = Field(default_factory=list)
    voice_states: list[Mapping[str, object]] = Field(default_factory=list)
    presences: list[Mapping[str, object]] = Field(default_factory=list)


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


class GuildCreatePayload(TypedDict):
    """The raw ``d`` payload of a GUILD_CREATE dispatch, as delivered by the gateway (subset)."""

    id: str
    name: str
    owner_id: str
    joined_at: NotRequired[str]
    large: NotRequired[bool]
    unavailable: NotRequired[bool]
    member_count: NotRequired[int]
    channels: NotRequired[list[Mapping[str, object]]]
    members: NotRequired[list[Mapping[str, object]]]
    voice_states: NotRequired[list[Mapping[str, object]]]
    presences: NotRequired[list[Mapping[str, object]]]


class EventName(StrEnum):
    """Every dispatch event name Discord currently defines.

    READY is deliberately not a member here - it's parsed once via
    :func:`~wd_discord.gateway.connection.parse_ready` before the continuous receive loop starts,
    and never appears again on the same connection, so it has no need of a dispatch-time lookup.

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

    MESSAGE_CREATE = ("MESSAGE_CREATE", Message)
    GUILD_CREATE = ("GUILD_CREATE", GuildCreate)

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

    INTERACTION_CREATE = "INTERACTION_CREATE"

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
    VOICE_STATE_UPDATE = "VOICE_STATE_UPDATE"
    VOICE_SERVER_UPDATE = "VOICE_SERVER_UPDATE"

    WEBHOOKS_UPDATE = "WEBHOOKS_UPDATE"
