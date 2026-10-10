# Typed @overload signatures for wd_bot.listener.listener.
#
# GENERATED FILE - do not hand-edit. Regenerate with:
#
#     uv run wd-bot/scripts/generate_listener_overloads.py
#
# One overload per event wd_discord.entities.bind wraps in an entity (wd_discord.entities.event_entities()).
# Every other event falls through to the general bare-name overload below.
# (no module docstring here on purpose - ruff's PYI021 flags docstrings in stub files)

from collections.abc import Awaitable, Callable
from typing import Any, Literal, overload

from wd_discord.entities import (
    AnyInteraction,
    Channel,
    ChannelPinsUpdate,
    GatewayGuild,
    Guild,
    GuildDelete,
    Message,
    Ready,
    ThreadCreate,
    ThreadDelete,
    ThreadListSync,
    ThreadMember,
    ThreadMembersUpdate,
    VoiceChannelStartTimeUpdate,
    VoiceChannelStatusUpdate,
    VoiceState,
)
from wd_discord.gateway import EventName

type _BoundHandler[T] = Callable[[Any, T], Awaitable[None]]

@overload
def listener(name: Literal[EventName.READY]) -> Callable[[_BoundHandler[Ready]], _BoundHandler[Ready]]: ...
@overload
def listener(name: Literal[EventName.MESSAGE_CREATE]) -> Callable[[_BoundHandler[Message]], _BoundHandler[Message]]: ...
@overload
def listener(name: Literal[EventName.GUILD_CREATE]) -> Callable[[_BoundHandler[GatewayGuild]], _BoundHandler[GatewayGuild]]: ...
@overload
def listener(
    name: Literal[EventName.INTERACTION_CREATE],
) -> Callable[[_BoundHandler[AnyInteraction]], _BoundHandler[AnyInteraction]]: ...
@overload
def listener(
    name: Literal[EventName.VOICE_STATE_UPDATE],
) -> Callable[[_BoundHandler[VoiceState]], _BoundHandler[VoiceState]]: ...
@overload
def listener(name: Literal[EventName.GUILD_UPDATE]) -> Callable[[_BoundHandler[Guild]], _BoundHandler[Guild]]: ...
@overload
def listener(name: Literal[EventName.GUILD_DELETE]) -> Callable[[_BoundHandler[GuildDelete]], _BoundHandler[GuildDelete]]: ...
@overload
def listener(name: Literal[EventName.CHANNEL_CREATE]) -> Callable[[_BoundHandler[Channel]], _BoundHandler[Channel]]: ...
@overload
def listener(name: Literal[EventName.CHANNEL_UPDATE]) -> Callable[[_BoundHandler[Channel]], _BoundHandler[Channel]]: ...
@overload
def listener(name: Literal[EventName.CHANNEL_DELETE]) -> Callable[[_BoundHandler[Channel]], _BoundHandler[Channel]]: ...
@overload
def listener(
    name: Literal[EventName.CHANNEL_PINS_UPDATE],
) -> Callable[[_BoundHandler[ChannelPinsUpdate]], _BoundHandler[ChannelPinsUpdate]]: ...
@overload
def listener(
    name: Literal[EventName.THREAD_CREATE],
) -> Callable[[_BoundHandler[ThreadCreate]], _BoundHandler[ThreadCreate]]: ...
@overload
def listener(name: Literal[EventName.THREAD_UPDATE]) -> Callable[[_BoundHandler[Channel]], _BoundHandler[Channel]]: ...
@overload
def listener(
    name: Literal[EventName.THREAD_DELETE],
) -> Callable[[_BoundHandler[ThreadDelete]], _BoundHandler[ThreadDelete]]: ...
@overload
def listener(
    name: Literal[EventName.THREAD_LIST_SYNC],
) -> Callable[[_BoundHandler[ThreadListSync]], _BoundHandler[ThreadListSync]]: ...
@overload
def listener(
    name: Literal[EventName.THREAD_MEMBER_UPDATE],
) -> Callable[[_BoundHandler[ThreadMember]], _BoundHandler[ThreadMember]]: ...
@overload
def listener(
    name: Literal[EventName.THREAD_MEMBERS_UPDATE],
) -> Callable[[_BoundHandler[ThreadMembersUpdate]], _BoundHandler[ThreadMembersUpdate]]: ...
@overload
def listener(
    name: Literal[EventName.VOICE_CHANNEL_STATUS_UPDATE],
) -> Callable[[_BoundHandler[VoiceChannelStatusUpdate]], _BoundHandler[VoiceChannelStatusUpdate]]: ...
@overload
def listener(
    name: Literal[EventName.VOICE_CHANNEL_START_TIME_UPDATE],
) -> Callable[[_BoundHandler[VoiceChannelStartTimeUpdate]], _BoundHandler[VoiceChannelStartTimeUpdate]]: ...
@overload
def listener[F: Callable[..., Awaitable[None]]](name: str | None = ...) -> Callable[[F], F]: ...
