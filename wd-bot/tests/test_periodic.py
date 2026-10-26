"""Behaviour tests: a cog's periodic task runs while the cog is loaded on a Bot, and survives a failing tick."""

import asyncio
import logging

import pytest
from wd_bot.bot import Bot
from wd_bot.cogs import Cog
from wd_bot.guard import dispatch_guard
from wd_discord.testing import RecordingClient


class _Ticker(Cog, auto_load=False):
    """Counts its ticks; the first ``failures`` of them raise."""

    failures = 0

    def __init__(self, *, bot: Bot) -> None:
        super().__init__(bot=bot)
        self.ticks = 0

    @Cog.periodic(seconds=0)
    async def tick(self) -> None:
        self.ticks += 1
        if self.ticks <= self.failures:
            msg = f"tick {self.ticks} broke"
            raise RuntimeError(msg)


def _make_bot() -> Bot:
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    bot.client = RecordingClient()
    return bot


async def _let_it_run() -> None:
    for _ in range(10):
        await asyncio.sleep(0)


async def test_loading_a_cog_starts_its_periodic_task_and_unloading_stops_it() -> None:
    bot = _make_bot()
    cog = _Ticker(bot=bot)

    await bot.add_cog(cog)
    await _let_it_run()
    assert cog.ticks > 1

    await bot.remove_cog(cog)
    stopped_at = cog.ticks
    await _let_it_run()
    assert cog.ticks == stopped_at


async def test_a_raising_tick_is_logged_and_the_loop_goes_on(caplog: pytest.LogCaptureFixture) -> None:
    bot = _make_bot()
    cog = _Ticker(bot=bot)
    cog.failures = 1

    dispatch_guard.logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.ERROR):
            await bot.add_cog(cog)
            await _let_it_run()
            await bot.remove_cog(cog)
    finally:
        dispatch_guard.logger.removeHandler(caplog.handler)

    assert cog.ticks > 1
    assert "_Ticker.tick" in caplog.text
    assert "tick 1 broke" in caplog.text


class _Scheduler(Cog, auto_load=False):
    """Asks for a long wait after its first tick, so it ticks once while loaded."""

    def __init__(self, *, bot: Bot) -> None:
        super().__init__(bot=bot)
        self.ticks = 0

    @Cog.periodic(seconds=0)
    async def tick(self) -> float:
        self.ticks += 1
        return 3600


async def test_a_tick_can_choose_how_long_to_wait_before_the_next() -> None:
    bot = _make_bot()
    cog = _Scheduler(bot=bot)

    await bot.add_cog(cog)
    await _let_it_run()
    await bot.remove_cog(cog)

    assert cog.ticks == 1
