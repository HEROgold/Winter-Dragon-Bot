"""Periodic tasks: a Cog method the bot runs on an interval for as long as the cog is loaded.

A cog declares the interval and the tick; :meth:`wd_bot.bot.Bot.add_cog` starts the task after the cog's
:meth:`~wd_bot.cogs.Cog.load`, and :meth:`~wd_bot.bot.Bot.remove_cog` cancels and awaits it before the cog's
:meth:`~wd_bot.cogs.Cog.unload`, so reloading a cog never leaves a second loop running. A tick that raises is logged
through :data:`~wd_bot.guard.dispatch_guard` and the loop goes on.
"""

lazy import asyncio
lazy from functools import partial
lazy from typing import TYPE_CHECKING, Self, overload

lazy from wd_bot.guard import dispatch_guard


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable

    lazy from wd_bot.cogs import Cog


type Seconds = float | Callable[[], float]
"""A wait in seconds, or a function returning it, read again before every wait (e.g. a live config value)."""


class PeriodicTask:
    """A Cog method run every :attr:`seconds` while its cog is loaded, starting right after the cog loads.

    Built by :meth:`wd_bot.cogs.Cog.periodic`. The tick is called as ``func(cog)``; when it returns a number, that is
    the wait in seconds before the next tick instead of :attr:`seconds` (for schedules that aren't a fixed interval).
    """

    def __init__(self, func: Callable[[Cog], Awaitable[float | None]], *, seconds: Seconds) -> None:
        """Wrap ``func`` as a tick repeated every ``seconds``."""
        self.func = func
        self.seconds = seconds

    @overload
    def __get__(self, instance: None, owner: type[Cog]) -> Self: ...
    @overload
    def __get__(self, instance: Cog, owner: type[Cog]) -> Callable[[], Awaitable[float | None]]: ...
    def __get__(self, instance: Cog | None, owner: type[Cog]) -> Self | Callable[[], Awaitable[float | None]]:
        """On the class, this task; on a cog, its tick bound to that cog, so ``await cog.tick()`` runs one tick."""
        return self if instance is None else partial(self.func, instance)

    @property
    def name(self) -> str:
        """The tick method's name."""
        return self.func.__name__

    def interval(self) -> float:
        """Return the default wait between two ticks, in seconds."""
        return self.seconds() if callable(self.seconds) else self.seconds

    def start(self, cog: Cog) -> asyncio.Task[None]:
        """Start ticking for ``cog`` on its bot's loop; cancel the returned task to stop."""
        return cog.bot.loop.create_task(self._run(cog), name=f"{cog.__cog_name__}.{self.name}")

    async def _run(self, cog: Cog) -> None:
        """Tick, then wait, forever; a tick that raises is logged and the next one runs as usual."""
        wait: float | None = None

        async def tick() -> None:
            nonlocal wait
            wait = await self.func(cog)

        while True:
            wait = None
            await dispatch_guard.run(f"periodic task '{cog.__cog_name__}.{self.name}'", tick)
            await asyncio.sleep(self.interval() if wait is None else wait)
