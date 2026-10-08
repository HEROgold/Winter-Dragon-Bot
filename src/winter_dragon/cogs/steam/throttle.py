"""Space out requests to Steam, and stop sending them for a while once Steam rate-limits us."""

from __future__ import annotations

lazy import asyncio
lazy import time
lazy from dataclasses import dataclass, field
lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable


INITIAL_BACKOFF_SECONDS = 300.0
"""How long requests pause after a rate-limit answer without a ``Retry-After``; doubles on each further one."""
MAX_BACKOFF_SECONDS = 3600.0 * 6


@dataclass
class RequestThrottle:
    """Lets requests through at least ``interval`` seconds apart, and none at all while paused by a rate limit.

    Steam blocks an IP that sends too many store requests (roughly one a second sustained); spacing requests keeps
    us under that, and pausing on a 429 keeps a block from growing.
    """

    interval: float
    """Minimum seconds between the starts of two requests."""
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    sent: int = 0
    """Requests let through so far."""
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _next_slot: float = field(default=0.0, init=False)
    _paused_until: float = field(default=0.0, init=False)
    _backoff: float = field(default=INITIAL_BACKOFF_SECONDS, init=False)

    @property
    def paused(self) -> bool:
        """Whether requests are paused after a rate-limit answer."""
        return self.clock() < self._paused_until

    async def acquire(self) -> bool:
        """Wait for the next request slot and claim it; ``False`` (without waiting) while paused."""
        async with self._lock:
            if self.paused:
                return False
            if (wait := self._next_slot - self.clock()) > 0:
                await self.sleep(wait)
            self._next_slot = self.clock() + self.interval
            self.sent += 1
            return True

    def rate_limited(self, retry_after: float | None) -> float:
        """Pause requests for ``retry_after`` seconds, or the current backoff when Steam didn't say; return the pause."""
        pause = retry_after if retry_after is not None and retry_after > 0 else self._backoff
        self._backoff = min(self._backoff * 2, MAX_BACKOFF_SECONDS)
        self._paused_until = self.clock() + pause
        return pause

    def succeeded(self) -> None:
        """Reset the backoff after a request Steam answered normally."""
        self._backoff = INITIAL_BACKOFF_SECONDS
