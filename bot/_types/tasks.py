"""Add error handling from discord tasks."""


import asyncio
import datetime
from collections.abc import Callable, Sequence

from discord.ext import tasks
from discord.utils import MISSING

from bot._types.aliases import CoroutineFunction
from bot._types.mixins import LoggerMixin


class Loop[FT: CoroutineFunction](tasks.Loop, LoggerMixin):
    async def _error(self, *args) -> None:
        exception: Exception = args[-1]
        self.logger.error(
            "Unhandled exception in internal background task %r.",
            self.coro.__name__,
            exc_info=exception,
        )
        return await super()._error(*args)


    def _handle_task_result(self, task: asyncio.Task) -> None:
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
    def decorator[FT: CoroutineFunction](func: FT) -> Loop[FT]:
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
