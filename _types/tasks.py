"""
Add error handling from discord tasks
"""


import asyncio
import datetime
import logging
from collections.abc import Sequence

from discord.ext import tasks

from _types.typing import CoroutineFunction
from tools.config_reader import config


class Loop(tasks.Loop):
    logger: logging.Logger


    def __init__(  # noqa: PLR0913
        self,
        coro: CoroutineFunction,
        seconds: float,
        hours: float,
        minutes: float,
        time: datetime.time | Sequence[datetime.time],
        count: int | None,
        reconnect: bool,
    ) -> None:
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.tasks")
        self.coro = coro
        # self.get_task().add_done_callback(self._handle_task_result) # doesn't seem to do anything
        super().__init__(coro, seconds, hours, minutes, time, count, reconnect)


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

