"""Gateway sharding (https://docs.discord.com/developers/events/gateway#sharding).

Discord routes guild events across separate gateway connections ("shards"): a guild lands on
``shard_id = (guild_id >> 22) % num_shards``, and events without a ``guild_id`` (DMs, etc.) go
to shard 0. Apps in 2500+ guilds *must* shard.

This module provides:

* the pure helpers :func:`shard_id_for_guild`, :func:`rate_limit_key`, :func:`identify_batches`,
  and :func:`parse_gateway_bot` (unit-testable without a socket),
* :class:`GatewayBotInfo`/:class:`SessionStartLimit` - a typed ``GET /gateway/bot`` response, and
* :class:`ShardManager` - creates one :class:`Gateway` per shard and IDENTIFYs them in
  ``max_concurrency``-sized batches spaced 5 seconds apart, as the rate limits require.
"""
from __future__ import annotations

lazy import asyncio
lazy from typing import TYPE_CHECKING, Any, Self

lazy from herogold.errors import with_known_exception

lazy from wd_discord.models import DiscordModel

lazy from .connection import Gateway


if TYPE_CHECKING:
    lazy from httpxyz import RequestError

    lazy from wd_discord.client import Client
    lazy from wd_discord.errors import ApiResponseError

    lazy from .connection import Ready

# Query string appended to the gateway URL from /gateway/bot (same pinning as DEFAULT_GATEWAY_URL).
GATEWAY_URL_QUERY = "?v=10&encoding=json"
# Seconds between IDENTIFY batches: max_concurrency IDENTIFYs are allowed per 5 seconds.
IDENTIFY_BATCH_DELAY = 5.0


def shard_id_for_guild(guild_id: int, num_shards: int) -> int:
    """Return the shard a guild's events are routed to: ``(guild_id >> 22) % num_shards``."""
    return (guild_id >> 22) % num_shards


def rate_limit_key(shard_id: int, max_concurrency: int) -> int:
    """Return a shard's IDENTIFY rate-limit bucket: ``shard_id % max_concurrency``."""
    return shard_id % max_concurrency


def identify_batches(shard_ids: list[int], max_concurrency: int) -> list[list[int]]:
    """Group ``shard_ids`` (ascending) into batches that may IDENTIFY concurrently.

    Consecutive chunks of ``max_concurrency`` shards have pairwise-distinct
    :func:`rate_limit_key` values, so each chunk may start at once; successive
    chunks must wait :data:`IDENTIFY_BATCH_DELAY` seconds.
    """
    ordered = sorted(shard_ids)
    return [ordered[i : i + max_concurrency] for i in range(0, len(ordered), max_concurrency)]


class SessionStartLimit(DiscordModel):
    """The ``session_start_limit`` object from ``GET /gateway/bot``."""

    total: int
    remaining: int
    reset_after: int
    """Milliseconds until ``remaining`` resets to ``total``."""
    max_concurrency: int
    """IDENTIFYs allowed per 5 seconds."""


class GatewayBotInfo(DiscordModel):
    """The ``GET /gateway/bot`` response (API -> object via :func:`parse_gateway_bot`)."""

    url: str
    shards: int
    """Discord's recommended number of shards."""
    session_start_limit: SessionStartLimit

    @property
    def connect_url(self) -> str:
        """The WSS URL with the version/encoding query this library speaks."""
        return f"{self.url}{GATEWAY_URL_QUERY}"


def parse_gateway_bot(payload: dict[str, Any]) -> GatewayBotInfo:
    """Parse a ``GET /gateway/bot`` JSON body into a :class:`GatewayBotInfo` (API -> object)."""
    return GatewayBotInfo.model_validate(payload)


async def fetch_gateway_bot(client: Client) -> GatewayBotInfo | ApiResponseError | RequestError:
    """Fetch ``GET /gateway/bot``, passing request errors through as values.

    :meth:`Client.get_gateway_bot` already validates the body into a :class:`GatewayBotInfo`,
    so this is a thin passthrough kept for callers that hold a :class:`Client`.
    """
    return await client.get_gateway_bot()


class ShardManager:
    """Run one :class:`Gateway` per shard, respecting the IDENTIFY rate limits.

    Built from a :class:`GatewayBotInfo` (see :func:`fetch_gateway_bot`); defaults to
    Discord's recommended shard count. Usable as an async context manager, mirroring
    :class:`Gateway`.
    """

    def __init__(
        self,
        token: str,
        info: GatewayBotInfo,
        *,
        intents: Intents = 0,
        num_shards: int | None = None,
    ) -> None:
        """Create a manager for ``token``; ``num_shards`` overrides ``info.shards``."""
        self.token = token
        self.info = info
        self.intents = intents
        self.num_shards = num_shards if num_shards is not None else info.shards
        self.shards: list[Gateway] = []

    @with_known_exception(RuntimeError)
    def shard_for_guild(self, guild_id: int) -> Gateway:
        """Return the started shard handling ``guild_id``'s events."""
        if not self.shards:
            msg = "ShardManager is not started."
            raise RuntimeError(msg)
        return self.shards[shard_id_for_guild(guild_id, self.num_shards)]

    async def _start(self, *, presence: dict[str, Any] | None = None) -> list[Ready]:
        """Connect every shard and return their READYs (in shard-id order).

        IDENTIFYs are sent in :func:`identify_batches` order, waiting
        :data:`IDENTIFY_BATCH_DELAY` seconds between batches. Raises :class:`RuntimeError`
        when the daily session-start budget cannot cover the shard count, since burning
        through it resets the bot token.
        """
        limit = self.info.session_start_limit
        if limit.remaining < self.num_shards:
            msg = (
                f"Not enough session starts remaining ({limit.remaining}/{limit.total}) "
                f"for {self.num_shards} shards; resets in {limit.reset_after} ms."
            )
            raise RuntimeError(msg)

        self.shards = [
            Gateway(
                self.token,
                intents=self.intents,
                url=self.info.connect_url,
                shard=(shard_id, self.num_shards),
            )
            for shard_id in range(self.num_shards)
        ]

        readies: list[Ready] = []
        batches = identify_batches(list(range(self.num_shards)), limit.max_concurrency)
        for index, batch in enumerate(batches):
            if index:
                await asyncio.sleep(IDENTIFY_BATCH_DELAY)
            readies += await asyncio.gather(*(self.shards[shard_id].connect(presence=presence) for shard_id in batch))
        return readies

    async def _close(self) -> None:
        """Close every shard's connection."""
        await asyncio.gather(*(shard.close() for shard in self.shards))
        self.shards = []

    async def __aenter__(self) -> Self:
        """Start all shards on context entry."""
        await self._start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close all shards on context exit."""
        await self._close()
