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

from wd_discord.entities import AnyInteraction, Guild, Message, Ready, VoiceState
from wd_discord.gateway import EventName

type _BoundHandler[T] = Callable[[Any, T], Awaitable[None]]

@overload
def listener(name: Literal[EventName.READY]) -> Callable[[_BoundHandler[Ready]], _BoundHandler[Ready]]: ...
@overload
def listener(name: Literal[EventName.MESSAGE_CREATE]) -> Callable[[_BoundHandler[Message]], _BoundHandler[Message]]: ...
@overload
def listener(name: Literal[EventName.GUILD_CREATE]) -> Callable[[_BoundHandler[Guild]], _BoundHandler[Guild]]: ...
@overload
def listener(
    name: Literal[EventName.INTERACTION_CREATE],
) -> Callable[[_BoundHandler[AnyInteraction]], _BoundHandler[AnyInteraction]]: ...
@overload
def listener(
    name: Literal[EventName.VOICE_STATE_UPDATE],
) -> Callable[[_BoundHandler[VoiceState]], _BoundHandler[VoiceState]]: ...
@overload
def listener[F: Callable[..., Awaitable[None]]](name: str | None = ...) -> Callable[[F], F]: ...
