"""Typed gateway dispatch event payloads and event-name -> model resolution.

Discord's gateway sends DISPATCH frames (op 0) carrying an event name (``t``) and a JSON
payload (``d``). This module maps a handful of event names to typed :class:`DiscordModel`
payloads (mirroring the parsing style already used by :func:`~wd_discord.gateway.connection.parse_ready`
and :func:`~wd_discord.gateway.sharding.parse_gateway_bot`) and falls back to :class:`RawEvent`
for everything else, so an unmodeled event never crashes the receive loop.

:func:`parse_dispatch` is :func:`~typing.overload`-ed on the event *name* as a
:class:`~typing.Literal`, so a call site that passes a literal name (e.g.
``parse_dispatch("MESSAGE_CREATE", data)``) gets both its ``data`` argument checked against
that event's :class:`~typing.TypedDict` payload shape and a precisely-typed return value
(``Message``, not the general ``DiscordModel`` union). :meth:`Gateway.listen` itself dispatches
on a runtime ``str`` it read off the socket, not a literal, so it always resolves to the general
overload - Python's type system can't narrow a return type off a value only known at runtime;
overloads-on-literals are the standard way to still get precise types wherever the event name
*is* known statically (call sites, tests, and - see ``wd_bot.cogs.listener`` - the point where a
handler is registered for one).

``User``/``Snowflake``/``Mapping`` are imported eagerly (not via ``lazy from``) because pydantic
resolves model field annotations to real classes at class-definition time; a still-unresolved
lazy-import proxy fails schema generation (``PydanticSchemaGenerationError``). ``Guild``/``Channel``
have this same problem internally today (pre-existing, unrelated to this change), so
:class:`GuildCreate` intentionally does not subclass :class:`~wd_discord.guild.Guild` or type its
nested collections as ``list[Channel]`` - see the TODO below.
"""

from __future__ import annotations

from collections.abc import Mapping
lazy from enum import StrEnum
lazy from typing import Literal, NotRequired, TypedDict, overload

lazy from pydantic import Field

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake
from wd_discord.user import User


class EventName(StrEnum):
    """Dispatch event names :mod:`wd_discord.gateway.events` has a typed payload model for.

    Not every event Discord sends - only the ones with an entry in this module (see
    :data:`_EVENT_MODELS`/the :func:`parse_dispatch` overloads below, and
    ``wd_bot.cogs.listener``, which key off these same members for compile-time payload
    checking). An event name absent here still dispatches - just as a :class:`RawEvent`, with
    no typed model and no listener-signature checking - it doesn't need a member added to work,
    only to get the stronger typing.
    """

    MESSAGE_CREATE = "MESSAGE_CREATE"
    GUILD_CREATE = "GUILD_CREATE"


class RawEvent(DiscordModel):
    """Fallback for any dispatch event without a dedicated model."""

    name: str
    data: Mapping[str, object]


class GuildCreate(DiscordModel):
    """GUILD_CREATE (subset - https://docs.discord.com/developers/events/gateway-events#guild-create).

    TODO(Phase 2): should subclass :class:`~wd_discord.guild.Guild` and type ``channels`` as
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
    :func:`parse_dispatch`'s ``data`` param directly off the pydantic model) so callers get a
    plain-dict shape to construct without needing pydantic, and so the wire shape and the parsed
    model can diverge (e.g. ``author`` here is the raw nested user object, not a ``User``).
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


# Runtime-only backing store for the general (non-literal-name) overload below. Keyed by
# EventName (a str subtype, so plain-str lookups from Gateway.listen() still work) purely for
# readability/consistency with the members below - the name -> TypedDict/model pairing that
# actually matters for type-checking lives in the @overload signatures underneath, not here.
_EVENT_MODELS: dict[str, type[DiscordModel]] = {
    EventName.GUILD_CREATE: GuildCreate,
    EventName.MESSAGE_CREATE: Message,
}


@overload
def parse_dispatch(name: Literal[EventName.MESSAGE_CREATE], data: MessageCreatePayload) -> Message: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_CREATE], data: GuildCreatePayload) -> GuildCreate: ...
@overload
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel: ...
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel:
    """Parse a dispatch (``t``, ``d``) pair into its typed model, or a :class:`RawEvent` fallback.

    READY is intentionally not handled here - it's parsed once via
    :func:`~wd_discord.gateway.connection.parse_ready` before the continuous receive loop starts,
    and never appears again on the same connection.
    """
    model = _EVENT_MODELS.get(name)
    if model is None:
        return RawEvent(name=name, data=data)
    return model.model_validate(data)
