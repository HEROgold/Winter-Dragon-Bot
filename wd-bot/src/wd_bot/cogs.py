"""Module that contains Cogs: wd-native feature units with no discord.ext.commands dependency."""

from __future__ import annotations

lazy from enum import IntFlag, auto
lazy from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    NotRequired,
    Protocol,
    Required,
    Self,
    TypedDict,
    Unpack,
    cast,
    overload,
)

lazy from herogold.log import LoggerMixin
lazy from sqlmodel import Session
lazy from wd_db.constants import engine

lazy from wd_bot.auto_reload import AutoReloadWatcher


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable

    lazy from wd_discord.gateway import EventName, GuildCreate, Message

    lazy from wd_bot.bot import Bot


class _Listener(Protocol):
    """A Cog method tagged by @listener() - callable, and carrying the event name it's tagged for."""

    __listener_event__: str
    __name__: str

    async def __call__(self, *args: object, **kwargs: object) -> None: ...


type _BoundHandler[T] = Callable[[Any, T], Awaitable[None]]
"""An (unbound) cog method's call shape: ``(self, payload: T) -> Awaitable[None]``.

``self`` has to be ``Any``, not the owning ``Cog`` subclass: parameter types are contravariant,
so a decorator expecting some fixed self-type could never accept a method whose ``self`` is a
*narrower* subclass of it - which is every real method. ``Any`` is the standard way around that
for exactly this shape of decorator; only the payload parameter is actually being checked here.
"""


class BotArgs(TypedDict):
    """TypedDict for bot arguments."""

    bot: Required[Bot]
    db_session: NotRequired[Session]


class CogFlags(IntFlag):
    """Flags for Cog behavior."""

    AutoLoad = auto()
    """Flag to indicate that the cog should be auto-loaded."""
    AutoReload = auto()
    """Flag to indicate that the cog should be auto-reloaded on file changes."""


default_flags = CogFlags(CogFlags.AutoLoad | CogFlags.AutoReload)


@overload
def listener(name: Literal[EventName.MESSAGE_CREATE]) -> Callable[[_BoundHandler[Message]], _BoundHandler[Message]]: ...
@overload
def listener(name: Literal[EventName.GUILD_CREATE]) -> Callable[[_BoundHandler[GuildCreate]], _BoundHandler[GuildCreate]]: ...
@overload
def listener[F: Callable[..., Awaitable[None]]](name: str | None = None) -> Callable[[F], F]: ...
def listener(name: str | None = None) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]:
    """Tag a Cog method as a gateway dispatch-event listener.

    Pass a :class:`~wd_discord.gateway.EventName` member explicitly
    (``@Cog.listener(EventName.MESSAGE_CREATE)``) to get the handler's payload parameter checked
    against that event's actual payload type - the overloads above reject e.g.
    ``async def on_message_create(self, message: GuildCreate)``. Called bare (``@Cog.listener()``)
    the event name is inferred from the method name instead (``on_message_create`` ->
    ``"MESSAGE_CREATE"``), with no payload-type checking: there's no literal name for an overload
    to key off, and this is also the only option for events wd_discord.gateway.events doesn't
    model yet (they only ever reach a listener as a RawEvent, with no EventName member to pass).
    A plain ``str`` also still works here for exactly that reason - EventName only covers modeled
    events, and this decorator has to keep working for the ones it doesn't cover yet too.

    TODO: add an overload above for each event wd_discord.gateway.events gains a typed model
    for (and a matching EventName member there). This is a bare attribute tag at runtime either
    way - see wd_bot.bot.Bot._listeners for why the registry itself can't be made fully sound (a
    dict keyed by a runtime string can't statically track which payload type belongs to which
    key; the type-checking that matters happens here, at registration).
    """

    def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        tagged = cast("_Listener", func)
        tagged.__listener_event__ = name or tagged.__name__.removeprefix("on_").upper()
        return func

    return decorator


class Cog(LoggerMixin):
    """A wd-native feature unit: a class whose methods can be tagged with @Cog.listener()."""

    bot: Bot
    flags: CogFlags = default_flags
    __cog_name__: ClassVar[str]
    # Deliberately not staticmethod(listener): `Cog.listener(...)` is always accessed via the
    # class (never an instance) at class-body-decoration time, so a plain function attribute
    # already behaves correctly without it - and `ty` currently loses @overload resolution on a
    # staticmethod-wrapped overloaded function (confirmed: identical overloads type-check fine
    # as a bare class attribute, wrong as soon as staticmethod() wraps them).
    listener = listener

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Cog instance with a bot reference and a database session."""
        self.bot = kwargs["bot"]
        self.session = kwargs.get("db_session", Session(engine))
        self._auto_reloader = AutoReloadWatcher(bot=self.bot, cog_cls=type(self))

        # Don't start the auto_load loop for the abstract/base Cog classes
        # (we only want concrete subclasses to be able to auto-load themselves).
        if self.__class__ not in (Cog, GroupCog):
            self.bot.loop.create_task(self.auto_load())
            self._auto_reloader.register()

    def __init_subclass__(cls: type[Self], *, auto_load: bool = True, flags: CogFlags | None = None) -> None:
        """Configure loader and hot-reload behavior for subclasses."""
        super().__init_subclass__()
        cls.__cog_name__ = cls.__name__
        if flags:
            cls.flags = flags
        if auto_load:
            cls.flags |= CogFlags.AutoLoad
        else:
            cls.flags &= ~CogFlags.AutoLoad

    async def auto_load(self) -> None:
        """Load the cog if auto_load is True."""
        if self.__cog_name__ in self.bot.cogs:
            return
        if self.flags & CogFlags.AutoLoad:
            self.logger.debug(t"Auto loaded Cog {type(self).__name__}")
            await self.bot.add_cog(self)

    async def cog_load(self) -> None:
        """Run setup once registered with the bot; a hook for subclasses to override.

        No-op by default: there's no CommandTree yet to sync app commands against.
        """

    async def cog_unload(self) -> None:
        """Unregister any auto-reload watcher."""
        self._auto_reloader.deregister()


class GroupCog(Cog):
    """Marker subclass for future app-command-group cogs (Phase 2)."""
