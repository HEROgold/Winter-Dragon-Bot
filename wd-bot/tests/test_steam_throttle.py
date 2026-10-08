"""Unit tests: spacing requests to Steam and pausing them after a rate limit (fake clock, no sleeping)."""

from __future__ import annotations

from winter_dragon.cogs.steam.throttle import INITIAL_BACKOFF_SECONDS, RequestThrottle


class FakeClock:
    """A monotonic clock that only moves when slept on or advanced."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _throttle(interval: float = 2.0) -> tuple[RequestThrottle, FakeClock]:
    clock = FakeClock()
    return RequestThrottle(interval, clock=clock, sleep=clock.sleep), clock


async def test_requests_are_spaced_by_the_interval() -> None:
    throttle, clock = _throttle()
    assert await throttle.acquire()
    clock.now += 0.5
    assert await throttle.acquire()
    assert clock.slept == [1.5]
    assert throttle.sent == 2


async def test_no_wait_once_the_interval_passed() -> None:
    throttle, clock = _throttle()
    await throttle.acquire()
    clock.now += 5
    await throttle.acquire()
    assert clock.slept == []


async def test_retry_after_pauses_requests_for_that_long() -> None:
    throttle, clock = _throttle()
    assert throttle.rate_limited(30) == 30
    assert not await throttle.acquire()
    clock.now += 30
    assert await throttle.acquire()


async def test_backoff_doubles_until_a_request_succeeds() -> None:
    throttle, _clock = _throttle()
    assert throttle.rate_limited(None) == INITIAL_BACKOFF_SECONDS
    assert throttle.rate_limited(None) == 2 * INITIAL_BACKOFF_SECONDS
    throttle.succeeded()
    assert throttle.rate_limited(None) == INITIAL_BACKOFF_SECONDS
