"""Utilities for handling rate limits.

The HTTP API implements a process for limiting and preventing excessive requests in accordance with RFC 6585
(https://datatracker.ietf.org/doc/html/rfc6585#section-4).
API users that regularly hit and ignore rate limits will have their API keys revoked, and be blocked from the platform.
For more information on rate limiting of requests, please see the Rate Limits section.
(https://docs.discord.com/developers/topics/rate-limits)
"""
from __future__ import annotations

lazy from dataclasses import dataclass
lazy from enum import StrEnum, auto
lazy from typing import TYPE_CHECKING

lazy from wd_errors.base import BaseError

lazy from wd_discord.utils import XORError, xor


if TYPE_CHECKING:
    lazy from datetime import datetime, timedelta

    lazy from wd_discord.endpoints import Endpoint

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
    reset: datetime # in epoch seconds
    reset_after: timedelta # in seconds
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

class LocaleRateLimit:
    """Per endpoint rate limit information."""

    endpoint: Endpoint

class GlobalRateLimit:
    """https://docs.discord.com/developers/topics/rate-limits#global-rate-limit.

    All bots can make up to 50 requests per second to our API.
    If no authorization header is provided, then the limit is applied to the IP address.
    This is independent of any individual rate limit on a route.
    If your bot gets big enough, based on its functionality,
        it may be impossible to stay below 50 requests per second during normal operations.
    Global rate limit issues generally show up as repeatedly getting banned from the Discord API
        when your bot starts (see below).
    If your bot gets temporarily Cloudflare banned from the Discord API every once in a while,
        it is most likely not a global rate limit issue.
    You probably had a spike of errors that was not properly handled and hit our error threshold.
    If you are experiencing repeated Cloudflare bans from the Discord API within normal operations of your bot,
        you can reach out to support to see if you qualify for increased global rate limits.
    You can contact Discord support using https://dis.gd/rate-limit.
    Interaction endpoints are not bound to the bot's Global Rate Limit.
    """
