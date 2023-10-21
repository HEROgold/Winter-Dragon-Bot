"""
Add error handling from discord tasks
"""

import datetime
from collections.abc import Sequence
import logging
from typing import Any
from discord.ext import tasks
from tools.config_reader import config

class Loop(tasks.Loop):
    logger: logging.Logger


    def __init__(
        self,
        coro: Any,
        seconds: float,
        hours: float,
        minutes: float,
        time: datetime.time | Sequence[datetime.time],
        count: int | None,
        reconnect: bool
    ) -> None:
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.tasks")
        super().__init__(coro, seconds, hours, minutes, time, count, reconnect)


    async def _error(self, *args: Any) -> None:
        exception: Exception = args[-1]
        self.logger.error(
            'Unhandled exception in internal background task %r.',
            self.coro.__name__,
            exc_info=exception
        )
        return super()._error(*args)
