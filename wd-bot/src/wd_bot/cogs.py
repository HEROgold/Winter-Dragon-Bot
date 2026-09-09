"""Module that contains Cogs: wd-native feature units with no discord.ext.commands dependency."""

from __future__ import annotations

lazy from enum import IntFlag, auto
lazy from typing import TYPE_CHECKING, ClassVar, NotRequired, Protocol, Required, Self, TypedDict, Unpack, cast

lazy from herogold.log import LoggerMixin
lazy from sqlmodel import Session
lazy from wd_db.constants import engine

lazy from wd_bot.auto_reload import AutoReloadWatcher


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable

    lazy from wd_bot.bot import Bot


class _Listener(Protocol):
    """A Cog method tagged by @listener() - callable, and carrying the event name it's tagged for."""

    __listener_event__: str
    __name__: str

    async def __call__(self, *args: object, **kwargs: object) -> None: ...


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


def listener[F: Callable[..., Awaitable[None]]](name: str | None = None) -> Callable[[F], F]:
    """Tag a Cog method as a gateway dispatch-event listener.

    TODO: replace with a strictly-typed listener registry (the handler's signature checked
    against the dispatched event's payload type) once more dispatch events are modeled - this
    is intentionally a bare attribute tag for now, not a maintainable long-term design.
    """

    def decorator(func: F) -> F:
        tagged = cast("_Listener", func)
        tagged.__listener_event__ = name or tagged.__name__.removeprefix("on_").upper()
        return func

    return decorator


class Cog(LoggerMixin):
    """A wd-native feature unit: a class whose methods can be tagged with @Cog.listener()."""

    bot: Bot
    flags: CogFlags = default_flags
    __cog_name__: ClassVar[str]
    listener = staticmethod(listener)

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
