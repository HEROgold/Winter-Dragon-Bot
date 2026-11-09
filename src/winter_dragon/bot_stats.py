"""What the bot serves right now, read from its gateway cache: guilds, channels, members, shards and uptime.

``/botstats``, the dashboard's stats page and the Prometheus exporter all show one :class:`BotStats`, so their numbers
agree. The dashboard runs in another process without a gateway, so the bot stores its latest snapshot in
:class:`BotStatsSnapshot` for it to read.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
lazy from importlib.metadata import version

from pydantic import BaseModel
from sqlmodel import Field
from wd_db.extension.lifecycle import LifecycleModel
lazy from sqlmodel import Session
lazy from wd_db.extension.lifecycle import alive_by_id, upsert
lazy from wd_discord.gateway.events import GuildCreate
lazy from wd_types.clock import utc_now


if TYPE_CHECKING:
    lazy from sqlalchemy import Engine
    lazy from wd_bot.bot import Bot
    lazy from wd_discord.cache import GuildState, StateCache
    lazy from wd_discord.gateway.connection import Gateway
    lazy from wd_discord.gateway.sharding import ShardManager


class ShardStats(BaseModel, frozen=True):
    """One gateway shard: whether Discord still acknowledges its heartbeats, and how fast."""

    id: int
    alive: bool
    latency: float | None
    """Seconds from its last acknowledged heartbeat to the acknowledgement; ``None`` before the first."""

    @classmethod
    def of(cls, gateway: Gateway, index: int) -> ShardStats:
        """Read ``gateway``, the ``index``-th shard; its ID is the one it identified with, else ``index``."""
        return cls(id=gateway.shard[0] if gateway.shard else index, alive=gateway.alive, latency=gateway.latency)


class BotStats(BaseModel, frozen=True):
    """A snapshot of what the bot serves, built from the cache without a request to Discord."""

    taken_at: datetime
    launch_time: datetime
    version: str
    guilds: int
    unavailable_guilds: int
    """Guilds Discord reports as down in an outage; counted in :attr:`guilds` too."""
    channels: int
    threads: int
    members: int
    """The sum of each guild's member count. Someone in two guilds counts twice, so this is approximate."""
    cached_users: int
    """Distinct users among the cached members. Large guilds only send all their members with the members intent."""
    shards: tuple[ShardStats, ...]

    @property
    def uptime(self) -> timedelta:
        """How long the bot had been running when the snapshot was taken."""
        return self.taken_at - self.launch_time

    @property
    def shards_alive(self) -> int:
        """How many shards Discord still acknowledges."""
        return sum(shard.alive for shard in self.shards)

    @classmethod
    def of(cls, bot: Bot) -> BotStats:
        """Take a snapshot of ``bot``: its client's cache and its shards."""
        return cls.from_cache(bot.client.cache, bot.shard_manager, launch_time=bot.launch_time)

    @classmethod
    def from_cache(cls, cache: StateCache, shards: ShardManager | None, *, launch_time: datetime) -> BotStats:
        """Take a snapshot of ``cache`` and ``shards`` (``None`` before the gateway connects)."""
        states = list(cache.guilds.values())
        return cls(
            taken_at=utc_now(),
            launch_time=launch_time,
            version=version("winter-dragon"),
            guilds=len(states),
            unavailable_guilds=sum(state.unavailable for state in states),
            channels=sum(len(state.channels or {}) for state in states),
            threads=sum(len(state.threads or {}) for state in states),
            members=sum(member_count(state) for state in states),
            cached_users=len({user_id for state in states for user_id in state.members}),
            shards=tuple(ShardStats.of(gateway, index) for index, gateway in enumerate(shards.shards if shards else [])),
        )


def member_count(state: GuildState) -> int:
    """Return how many members ``state``'s guild has: as GUILD_CREATE or a counted fetch said, else as cached."""
    guild = state.guild
    if isinstance(guild, GuildCreate) and guild.member_count is not None:
        return guild.member_count
    if guild.approximate_member_count is not None:
        return guild.approximate_member_count
    return len(state.members)


SNAPSHOT_ID = 1
"""The ID of the one :class:`BotStatsSnapshot` row; each snapshot overwrites the one before."""


class BotStatsSnapshot(LifecycleModel, table=True):
    """The bot's latest :class:`BotStats`, for the dashboard; shared data, owned by no one.

    The snapshot is kept as JSON, so a new :class:`BotStats` field needs no migration.
    """

    stats: str = Field(default="")
    """The :class:`BotStats`, as JSON."""


def store_snapshot(session: Session, stats: BotStats) -> None:
    """Make ``stats`` the latest snapshot. The caller commits."""
    upsert(session, BotStatsSnapshot(id=SNAPSHOT_ID, stats=stats.model_dump_json()))


def latest_snapshot(bind: Engine) -> BotStats | None:
    """Return the latest snapshot the bot stored; ``None`` before its first."""
    with Session(bind) as session:
        row = alive_by_id(session, BotStatsSnapshot, SNAPSHOT_ID)
    return None if row is None else BotStats.model_validate_json(row.stats)
