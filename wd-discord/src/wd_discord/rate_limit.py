"""Utilities for handling rate limits.

The HTTP API implements a process for limiting and preventing excessive requests in accordance with RFC 6585
(https://datatracker.ietf.org/doc/html/rfc6585#section-4).
API users that regularly hit and ignore rate limits will have their API keys revoked, and be blocked from the platform.
For more information on rate limiting of requests, please see the Rate Limits section.
(https://docs.discord.com/developers/topics/rate-limits)
"""

from __future__ import annotations

lazy import asyncio
lazy import time
lazy from abc import ABC, abstractmethod
lazy from collections import deque
lazy from dataclasses import dataclass, field
lazy from enum import StrEnum, auto
lazy from http import HTTPStatus
lazy from typing import TYPE_CHECKING, Any, ClassVar

lazy from herogold.log import LoggerMixin, getLogger
lazy from wd_errors.base import BaseError

lazy from wd_discord.utils import XORError, xor


if TYPE_CHECKING:
    lazy from collections.abc import Callable, Mapping
    lazy from datetime import datetime, timedelta
    lazy from types import CoroutineType

    lazy from httpxyz import Headers, Response

logger = getLogger("RateLimit")


class Buckets(StrEnum):
    """Represents the different buckets for rate limits."""

    global_ = auto()
    per_endpoint = auto()
    per_user = auto()
    shared = auto()


class ScopeError(BaseError):
    """Raised when both _global and _scope are set or when neither are set in a HeaderFormat."""

    def __init__(self, global_: bool | None, scope: str | None) -> None:  # noqa: FBT001
        """Initialize the error."""
        super().__init__(f"Invalid scope: global={global_}, scope={scope}. Exactly one of these must be set.")


@dataclass
class HeaderFormat:
    """Example header format for rate limits.

    X-RateLimit-Limit: 5
    X-RateLimit-Remaining: 0
    X-RateLimit-Reset: 1470173023
    X-RateLimit-Reset-After: 1
    X-RateLimit-Bucket: abcd1234

    X-RateLimit-Global - Returned only on HTTP 429 responses if the rate limit encountered is the global rate limit
        (not per-route)
    X-RateLimit-Scope - Returned only on HTTP 429 responses. Value can be user (per bot or user limit),
        global(per bot or user global limit), or shared (per resource limit)
    """

    limit: int
    remaining: int
    reset: datetime  # in epoch seconds
    reset_after: timedelta  # in seconds
    bucket: Buckets
    _global: bool | None = None
    _scope: str | None = None

    @property
    def scope(self) -> str:
        """Get the scope of the rate limit."""
        scope = xor(self._global, bool(self._scope))
        if isinstance(scope, XORError):
            raise ScopeError(self._global, self._scope)
        if not self._scope:
            return "global"
        return self._scope


class RateLimiter(ABC):
    """A rate-limit strategy :class:`~wd_discord.client.Client` consults around each request.

    Discord's docs (https://docs.discord.com/developers/topics/rate-limits) say limits should
    not be hard-coded: a client should parse response headers and track remaining/reset per
    bucket to avoid hitting the limit in the first place, and fall back to the ``retry_after``
    field of a 429 body when it happens anyway (races, an unseen route, or a scope Discord never
    signals proactively).
    """

    @abstractmethod
    async def acquire(self, key: RouteKey) -> None:
        """Block until it's safe to send a request identified by ``key``."""

    @abstractmethod
    def update(self, key: RouteKey, headers: Mapping[str, str]) -> None:
        """Record any rate-limit state visible in a response's headers for ``key``."""

    @abstractmethod
    async def on_429(self, key: RouteKey, retry_after: float) -> None:
        """Handle being rate limited on ``key``: warn, then wait the fallback ``retry_after``."""


GLOBAL_REQUESTS_PER_SECOND = 50
"""https://docs.discord.com/developers/topics/rate-limits#global-rate-limit.

All bots can make up to 50 requests per second to the API, independent of any individual
rate limit on a route. Interaction endpoints are exempt from this limit.
"""


@dataclass
class GlobalRateLimiter(RateLimiter):
    """Proactively caps outgoing requests to Discord's global rate limit.

    Discord never sends a proactive header for this limit (only reactively, via a 429 with
    ``global=true``) - so unlike :class:`BucketRateLimiter`, the only way to avoid it is to
    self-impose the ceiling client-side, via a sliding one-second window of send timestamps.
    """

    limit: int = GLOBAL_REQUESTS_PER_SECOND
    _sent: deque[float] = field(default_factory=deque)

    async def acquire(self, key: RouteKey) -> None:  # noqa: ARG002 - one global limit, no per-key state
        """Wait until sending would keep the last second's request count under ``limit``."""
        while True:
            now = time.monotonic()
            while self._sent and now - self._sent[0] >= 1:
                self._sent.popleft()
            if len(self._sent) < self.limit:
                self._sent.append(now)
                return
            wait = 1 - (now - self._sent[0])
            logger.warning(t"Approaching global rate limit; waiting {wait:.3f}s")
            await asyncio.sleep(wait)

    def update(self, key: RouteKey, headers: Mapping[str, str]) -> None:
        """No-op: Discord never sends a proactive global-remaining header."""

    async def on_429(self, key: RouteKey, retry_after: float) -> None:  # noqa: ARG002 - global, no per-key state
        """Fallback path: warn and wait Discord's own ``retry_after`` for the global limit."""
        logger.warning(t"Hit the global rate limit; retrying in {retry_after:.3f}s")
        await asyncio.sleep(retry_after)


@dataclass
class BucketRateLimiter(RateLimiter):
    """Proactively tracks per-route rate limits using Discord's ``X-RateLimit-*`` headers.

    Routes that share a Discord-assigned bucket (``X-RateLimit-Bucket``) share their remaining/
    reset state here too, even if their ``key`` differs - the bucket id, not the key, is what
    :meth:`update` actually indexes state by. A route not seen before proceeds optimistically
    (nothing to wait on yet); its state is learned from the first response.
    """

    _route_buckets: dict[str, str] = field(default_factory=dict)
    _bucket_state: dict[str, tuple[int, float]] = field(default_factory=dict)
    """bucket id -> (remaining, reset time as a `time.monotonic()` value)."""

    async def acquire(self, key: RouteKey) -> None:
        """Wait until ``key``'s bucket resets, if a previously-learned bucket is exhausted."""
        bucket_id = self._route_buckets.get(key)
        if bucket_id is None:
            return
        state = self._bucket_state.get(bucket_id)
        if state is None:
            return
        remaining, reset_at = state
        if remaining > 0:
            return
        wait = reset_at - time.monotonic()
        if wait > 0:
            logger.warning(t"Route {key} rate limit bucket exhausted; waiting {wait:.3f}s for reset")
            await asyncio.sleep(wait)

    def update(self, key: RouteKey, headers: Mapping[str, str]) -> None:
        """Learn ``key``'s bucket id and refresh that bucket's remaining/reset from headers."""
        bucket_id = headers.get("X-RateLimit-Bucket")
        remaining = headers.get("X-RateLimit-Remaining")
        reset_after = headers.get("X-RateLimit-Reset-After")
        if bucket_id is None or remaining is None or reset_after is None:
            return
        self._route_buckets[key] = bucket_id
        self._bucket_state[bucket_id] = (int(remaining), time.monotonic() + float(reset_after))

    async def on_429(self, key: RouteKey, retry_after: float) -> None:
        """Fallback path: warn and wait Discord's own ``retry_after`` for this route."""
        logger.warning(t"Rate limited on route {key}; retrying in {retry_after:.3f}s")
        await asyncio.sleep(retry_after)


class SharedRateLimiter(RateLimiter):
    """Reacts to shared-resource 429s (``X-RateLimit-Scope: shared``, e.g. emoji limits).

    Discord gives no advance signal for these - they only ever surface as a 429 - so unlike
    :class:`BucketRateLimiter` there's nothing to track proactively. Kept as its own class
    because the docs call this scope out as distinct from a per-route limit (it's exempt from
    the separate invalid-request/Cloudflare-ban counter), even though the runtime behavior here
    is the same wait-and-warn fallback.
    """

    async def acquire(self, key: RouteKey) -> None:
        """No-op: nothing to track ahead of time for a shared-resource limit."""

    def update(self, key: RouteKey, headers: Mapping[str, str]) -> None:
        """No-op: same reasoning as :meth:`acquire`."""

    async def on_429(self, key: RouteKey, retry_after: float) -> None:
        """Fallback path: warn and wait Discord's own ``retry_after`` for this shared resource."""
        logger.warning(t"Shared resource rate limit hit for {key}; retrying in {retry_after:.3f}s")
        await asyncio.sleep(retry_after)


_MAJOR_PARAM_PREFIXES = ("guilds", "channels", "webhooks")

MAX_RATE_LIMIT_RETRIES = 5


class RouteKey(str):
    """A string that uniquely identifies a Discord rate-limit bucket.

    Discord's rate-limiting rules (https://docs.discord.com/developers/topics/rate-limits)
    partition buckets by the major parameter in the route (``guild_id``, ``channel_id``,
    or ``webhook_id``). All other path segments are collapsed to ``{id}`` so that unrelated
    IDs on an otherwise identical route don't fragment a single real Discord bucket into
    many local keys.
    """

    __slots__ = ()


def route_key(method: str, path: str) -> RouteKey:
    """Collapse a request to Discord's major-param route-key shape (method + path).

    Only ``guild_id``/``channel_id``/``webhook_id`` partition a Discord rate-limit bucket
    independently (https://docs.discord.com/developers/topics/rate-limits) - every other path
    segment (message ids, user ids, ``@me``, ...) is collapsed so unrelated ids on an otherwise
    identical route don't fragment a single real Discord bucket into many local keys.
    """
    segments = path.strip("/").split("/")
    keyed: list[str] = []
    keep_next = False
    for segment in segments:
        if keep_next:
            keyed.append(segment)
            keep_next = False
            continue
        if segment in _MAJOR_PARAM_PREFIXES:
            keyed.append(segment)
            keep_next = True
            continue
        keyed.append("{id}" if segment.isdigit() else segment)
    return RouteKey(f"{method} {'/'.join(keyed)}")


class MaxRetriesExceededError(Exception):
    """Raised when a request exceeds the maximum number of rate-limit retries."""


class RateLimitHandler(LoggerMixin):
    """Runs a single logical request through the rate-limit retry loop.

    Owns no shared mutable state on the underlying client - :meth:`send` calls the network
    function it's given directly, rather than patching :class:`~httpxyz.AsyncClient.request`.
    A previous version patched the client instead; under concurrency, multiple in-flight
    requests sharing one :class:`~httpxyz.AsyncClient` raced on that patch (each wrapping
    whatever the previous one had already wrapped), corrupting retry counts across unrelated
    requests. A fresh, unshared :class:`RateLimitHandler` per request - only the *limiters*
    themselves (class-level, intentionally shared so the whole client throttles together) -
    avoids that entirely: nothing here is written to except this instance's own ``tries``.
    """

    limiters: ClassVar[dict[str, RateLimiter]] = {}
    limiters["global"] = GlobalRateLimiter()
    limiters["bucket"] = BucketRateLimiter()
    limiters["shared"] = SharedRateLimiter()

    def __init__(self, key: RouteKey) -> None:
        """Initialize the rate limit handler with global, bucket, and shared limiters."""
        self.key = key
        self.tries = 0

    async def acquire(self) -> None:
        """Wait on every limiter for this handler's route key before sending."""
        for limiter in self.limiters.values():
            await limiter.acquire(self.key)

    def update(self, headers: Headers) -> None:
        """Update the rate limiters with the response headers for this handler's route key."""
        for limiter in self.limiters.values():
            limiter.update(self.key, headers)

    async def wait_on_rate_limit(self, response: Response) -> None:
        """Parse a 429's body/headers and wait via the matching limiter before retrying.

        ``retry_after`` from the JSON body is Discord's own authoritative fallback figure; the
        ``Retry-After`` header is used only if the body is missing or unparsable.
        """
        try:
            body = response.json()
        except Exception:  # noqa: BLE001 - a malformed 429 body shouldn't break the retry loop
            body = {}
        retry_after = float(body.get("retry_after", response.headers.get("Retry-After", 1)))

        global_, scope = body.get("global", False), response.headers.get("X-RateLimit-Scope")
        match global_, scope:
            case True, _:
                await self.limiters["global"].on_429(self.key, retry_after)
            case False, "shared":
                await self.limiters["shared"].on_429(self.key, retry_after)
            case False, _:
                await self.limiters["bucket"].on_429(self.key, retry_after)

    async def send[R: Response](self, func: Callable[[], CoroutineType[Any, Any, R]]) -> R:
        """Call ``func()`` under the rate-limit retry loop, waking it up to :data:`MAX_RATE_LIMIT_RETRIES` times.

        ``func`` takes no arguments (the caller closes over whatever it needs, e.g.
        ``lambda: self._client.request(method, path, **kwargs)``) - this method's only job is
        acquiring/updating the limiters and retrying on a 429, not building the request itself.
        """
        while self.tries < MAX_RATE_LIMIT_RETRIES:
            await self.acquire()
            response = await func()
            self.update(response.headers)

            if response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
                return response

            await self.wait_on_rate_limit(response)
            self.tries += 1
            backoff = 2**self.tries
            self.logger.warning(t"Backoff {backoff}s for {self.key} after 429 rate-limit response")
            await asyncio.sleep(backoff)
        msg = f"Exceeded {MAX_RATE_LIMIT_RETRIES} rate-limit retries for {self.key}"
        raise MaxRetriesExceededError(msg)
