# Typed @overload signatures for wd_bot.listener.listener.
#
# GENERATED FILE - do not hand-edit. Regenerate with:
#
#     uv run wd-bot/scripts/generate_listener_overloads.py
#
# One overload per EventName member that has a model wired up (EventName.X.model is not None) -
# mirrors wd-discord/scripts/generate_dispatch_overloads.py's dispatch.pyi (same source data).
# Members without a model fall through to the general bare-name overload below.
# (no module docstring here on purpose - ruff's PYI021 flags docstrings in stub files)

from collections.abc import Awaitable, Callable
from typing import Any, Literal, overload

from wd_discord.gateway import EventName, GuildCreate, Message

type _BoundHandler[T] = Callable[[Any, T], Awaitable[None]]

@overload
def listener(name: Literal[EventName.MESSAGE_CREATE]) -> Callable[[_BoundHandler[Message]], _BoundHandler[Message]]: ...
@overload
def listener(name: Literal[EventName.GUILD_CREATE]) -> Callable[[_BoundHandler[GuildCreate]], _BoundHandler[GuildCreate]]: ...
@overload
def listener[F: Callable[..., Awaitable[None]]](name: str | None = ...) -> Callable[[F], F]: ...
