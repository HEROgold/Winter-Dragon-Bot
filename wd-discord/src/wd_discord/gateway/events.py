"""Typed gateway dispatch event payloads and event-name -> model resolution.

Discord's gateway sends DISPATCH frames (op 0) carrying an event name (``t``) and a JSON
payload (``d``). This module maps a handful of event names to typed :class:`DiscordModel`
payloads (mirroring the parsing style already used by :func:`~wd_discord.gateway.connection.parse_ready`
and :func:`~wd_discord.gateway.sharding.parse_gateway_bot`) and falls back to :class:`RawEvent`
for everything else, so an unmodeled event never crashes the receive loop.

``User``/``Snowflake`` are imported eagerly (not via ``lazy from``) because pydantic resolves
model field annotations to real classes at class-definition time; a still-unresolved lazy-import
proxy fails schema generation (``PydanticSchemaGenerationError``). ``Guild``/``Channel`` have
this same problem internally today (pre-existing, unrelated to this change), so
:class:`GuildCreate` intentionally does not subclass :class:`~wd_discord.guild.Guild` or type its
nested collections as ``list[Channel]`` - see the TODO below.
"""
from __future__ import annotations

lazy from typing import Any

lazy from pydantic import Field

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake
from wd_discord.user import User


class RawEvent(DiscordModel):
    """Fallback for any dispatch event without a dedicated model."""

    name: str
    data: dict[str, Any]


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
    channels: list[dict[str, Any]] = Field(default_factory=list)
    members: list[dict[str, Any]] = Field(default_factory=list)
    voice_states: list[dict[str, Any]] = Field(default_factory=list)
    presences: list[dict[str, Any]] = Field(default_factory=list)


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


_EVENT_MODELS: dict[str, type[DiscordModel]] = {
    "GUILD_CREATE": GuildCreate,
    "MESSAGE_CREATE": Message,
}


def parse_dispatch(name: str, data: dict[str, Any]) -> DiscordModel:
    """Parse a dispatch (``t``, ``d``) pair into its typed model, or a :class:`RawEvent` fallback.

    READY is intentionally not handled here - it's parsed once via
    :func:`~wd_discord.gateway.connection.parse_ready` before the continuous receive loop starts,
    and never appears again on the same connection.
    """
    model = _EVENT_MODELS.get(name)
    if model is None:
        return RawEvent(name=name, data=data)
    return model.model_validate(data)
