"""Add error handling from discord tasks."""

import asyncio
import datetime
from collections.abc import Callable, Sequence
from typing import Any

from discord.ext import tasks
from discord.utils import MISSING
from winter_dragon.bot._types.aliases import CoroutineFunction
from winter_dragon.bot.core.log import LoggerMixin


class Loop[FT: CoroutineFunction](tasks.Loop, LoggerMixin):
    """Loop is a subclass of discord.ext.tasks.Loop that adds logging to the loop task."""

    def __init__(  # noqa: PLR0913
        self,
        coro: FT,
        *,
        seconds: float,
        hours: float,
        minutes: float,
        time: datetime.time | Sequence[datetime.time],
        count: int | None,
        reconnect: bool,
        name: str | None,
    ) -> None:
        """Initialize the Loop class."""
        super().__init__(coro, seconds, hours, minutes, time, count, reconnect, name)

    async def _error(self, *args: Exception) -> None:
        exception = args[-1]
        self.logger.error(
            "Unhandled exception in internal background task %r.",
            self.coro.__name__, # type: ignore[reportUnknownArgumentType]
            exc_info=exception,
        )
        return await super()._error(*args)

    def _handle_task_result(self, task: asyncio.Task[Any]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass  # Task cancellation should not be logged as an error.
        except Exception:  # pylint: disable=broad-except
            self.logger.exception("Exception raised by task: %r", task)


def loop[FT: CoroutineFunction](  # noqa: PLR0913
    *,
    seconds: float = 0,
    minutes: float = 0,
    hours: float = 0,
    time: datetime.time | Sequence[datetime.time] = MISSING,
    count: int | None = None,
    reconnect: bool = True,
    name: str | None = None,
) -> Callable[[FT], Loop[FT]]:
    """Schedule a new task to run every N seconds, minutes, or hours."""
    # FT generic type is used here and in the Loop class to ensure the coroutine function type is preserved.
    def decorator(func: FT) -> Loop[FT]:
        return Loop[FT](
            func,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            count=count,
            time=time,
            reconnect=reconnect,
            name=name,
        )

    return decorator
