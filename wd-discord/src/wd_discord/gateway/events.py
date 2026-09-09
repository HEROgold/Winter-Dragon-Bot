"""Typed gateway dispatch event payloads and event-name -> model resolution.

Discord's gateway sends DISPATCH frames (op 0) carrying an event name (``t``) and a JSON
payload (``d``). This module maps a handful of event names to typed :class:`DiscordModel`
payloads (mirroring the parsing style already used by :func:`~wd_discord.gateway.connection.parse_ready`
and :func:`~wd_discord.gateway.sharding.parse_gateway_bot`) and falls back to :class:`RawEvent`
for everything else, so an unmodeled event never crashes the receive loop.

:class:`EventName` is the single source of truth for a modeled event: each member carries its
own :class:`DiscordModel` subclass as a real attribute (``EventName.MESSAGE_CREATE.model is
Message``), via the "data-carrying enum" pattern (a custom ``__new__``) rather than a
separate name -> model dict living apart from the names themselves.

That covers the *runtime* mapping. The *static* one - :func:`parse_dispatch`'s ``data`` argument
checked against the right :class:`~typing.TypedDict` payload shape, and its return type narrowed
to ``Message``/``GuildCreate`` instead of the general ``DiscordModel`` union - still needs
:func:`~typing.overload` on ``Literal[EventName.X]``. That's not a stylistic choice: Python's
type checkers have no construct for "the return type is a function of this runtime value" other
than an overload (or the equivalent under another name, e.g. TypedDict-union narrowing on a
literal key) - `Annotated` metadata is inert to a checker's control-flow analysis; it's for
runtime introspection (pydantic, FastAPI, ...), not static return-type inference. This is the
same mechanism typeshed itself uses for e.g. ``open()``'s mode-dependent return type.
:meth:`Gateway.listen` dispatches on a runtime ``str`` it read off the socket, not a literal, so
it always resolves to the general (non-narrowed) overload - there's no literal there to narrow on.

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
lazy from typing import Literal, NotRequired, Self, TypedDict, overload

lazy from pydantic import Field

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake
from wd_discord.user import User


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


class EventName(StrEnum):
    """Dispatch event names :mod:`wd_discord.gateway.events` has a typed payload model for.

    Not every event Discord sends - only the ones modeled here. An event name absent from this
    enum still dispatches fine, just as a :class:`RawEvent` with no listener-signature checking
    (see ``wd_bot.cogs.listener``) - it doesn't need a member added to work, only to get the
    stronger typing.

    Each member carries its own :class:`DiscordModel` subclass as a real attribute
    (``EventName.MESSAGE_CREATE.model is Message``) via a custom ``__new__``, so the name and its
    model live in exactly one place. The matching payload TypedDict (``MessageCreatePayload``,
    ...) *isn't* attached the same way - TypedDicts have no runtime existence to attach; they only
    exist for the @overload signatures below to check a caller's ``data`` argument against.
    """

    model: type[DiscordModel]

    def __new__(cls, value: str, model: type[DiscordModel]) -> Self:
        """Build a member, attaching its ``model`` alongside the usual str ``value``."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.model = model
        return member

    MESSAGE_CREATE = ("MESSAGE_CREATE", Message)
    GUILD_CREATE = ("GUILD_CREATE", GuildCreate)


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
    try:
        event = EventName(name)
    except ValueError:
        return RawEvent(name=name, data=data)
    return event.model.model_validate(data)
