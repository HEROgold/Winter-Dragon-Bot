"""The owners' stats page: what the bot serves, from the latest snapshot it stored."""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

from fastapi import APIRouter
lazy from fastapi import Request
lazy from starlette.responses import Response  # noqa: TC002 - FastAPI resolves route annotations at runtime
lazy from wd_types.clock import utc_now

lazy from winter_dragon.bot_stats import latest_snapshot
lazy from winter_dragon.cogs.bot_stats import BotStatsSettings, shard_line
lazy from winter_dragon.web.accounts import BotOwner, visitor_zone
lazy from winter_dragon.web.formatting import span
lazy from winter_dragon.web.responses import Database, render


if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from winter_dragon.bot_stats import BotStats


router = APIRouter()

STALE_INTERVALS = 3
"""Snapshot intervals without a new snapshot before the page warns that the bot stopped storing them."""


@dataclass(frozen=True)
class StatsView:
    """The latest snapshot, and whether it's too old to trust."""

    stats: BotStats | None
    """``None`` until the bot stores its first snapshot."""
    age: timedelta | None
    stale: bool

    @classmethod
    def at(cls, stats: BotStats | None, now: datetime, interval: float) -> StatsView:
        """Return the view of ``stats`` at ``now``, stale past :data:`STALE_INTERVALS` times ``interval`` seconds."""
        if stats is None:
            return cls(stats=None, age=None, stale=True)
        age = now - stats.taken_at
        return cls(stats=stats, age=age, stale=age.total_seconds() > STALE_INTERVALS * interval)


@router.get("/bot")
def bot_stats_page(request: Request, _: BotOwner, bind: Database) -> Response:
    """Show the bot's owners what it serves: the counts, each shard, uptime and version."""
    view = StatsView.at(latest_snapshot(bind), utc_now(), BotStatsSettings.snapshot_interval)
    return render(
        request,
        "bot/page.html",
        view=view,
        shard_line=shard_line,
        span=span,
        zone=visitor_zone(request),
        interval=BotStatsSettings.snapshot_interval,
    )
