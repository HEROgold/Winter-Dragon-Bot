"""Add error handling from discord tasks."""

import asyncio
from collections.abc import Callable, Coroutine, Sequence
from typing import TYPE_CHECKING, Any

from discord.ext import tasks
from discord.utils import MISSING
from herogold.log import LoggerMixin


if TYPE_CHECKING:
    import datetime


type CoroutineFunction = Callable[..., Coroutine[Any, Any, Any]]


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
            self.coro.__name__,
            exc_info=exception,
        )
        return await super()._error(*args)

    def _handle_task_result[T](self, task: asyncio.Task[T]) -> T | None:
        try:
            return task.result()
        except asyncio.CancelledError:
            pass  # Task cancellation should not be logged as an error.
        except Exception:
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
