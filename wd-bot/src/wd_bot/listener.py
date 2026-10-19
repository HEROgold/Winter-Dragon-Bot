"""Runtime `listener()` decorator: tag a Cog method as a gateway dispatch-event listener.

The typed ``@overload`` signatures live in the paired ``listener.pyi`` - GENERATED, see
``wd-bot/scripts/generate_listener_overloads.py`` - not in this file. A stub file shadows its
paired ``.py`` module entirely for type checkers, so this module's own annotations on
:func:`listener` are irrelevant to callers; only the runtime behavior matters here.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, Protocol, cast


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable


class _Listener(Protocol):
    """A Cog method tagged by @listener() - callable, and carrying the event name it's tagged for."""

    __listener_event__: str
    __name__: str

    async def __call__(self, *args: object, **kwargs: object) -> None: ...


def listener(name: str | None = None) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]:
    """Tag a Cog method as a gateway dispatch-event listener.

    Pass a :class:`~wd_discord.gateway.EventName` member explicitly
    (``@Cog.listener(EventName.MESSAGE_CREATE)``) to get the handler's payload parameter checked
    against that event's actual payload type - see ``listener.pyi``'s generated overloads, which
    reject e.g. ``async def on_message_create(self, message: GuildCreate)``. Called bare
    (``@Cog.listener()``) the event name is inferred from the method name instead
    (``on_message_create`` -> ``"MESSAGE_CREATE"``), with no payload-type checking: there's no
    literal name for an overload to key off, and this is also the only option for events
    wd_discord.gateway.events doesn't model yet (they only ever reach a listener as a RawEvent,
    with no EventName member to pass). A plain ``str`` also still works here for exactly that
    reason - EventName only covers modeled events, and this decorator has to keep working for
    the ones it doesn't cover yet too.

    This is a bare attribute tag at runtime either way - see ``wd_bot.bot.Bot._listeners`` for
    why the registry itself can't be made fully sound (a dict keyed by a runtime string can't
    statically track which payload type belongs to which key; the type-checking that matters
    happens here, at registration).
    """

    def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        tagged = cast("_Listener", func)
        tagged.__listener_event__ = name or tagged.__name__.removeprefix("on_").upper()
        return func

    return decorator
