"""Unit tests: the privacy cog purges soft-deleted records 30 days after their deletion, and nothing else (sqlite)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, select
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive, create_or_restore

from winter_dragon.cogs.privacy import Privacy
from winter_dragon.cogs.reminder import Reminder
from winter_dragon.cogs.steam.models import SaleTypes, SteamSale, SteamSaleProperties


if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.engine.interfaces import DBAPIConnection
    from sqlalchemy.pool import ConnectionPoolEntry
    from wd_bot.auto_reload import AutoReloadWatcher


DAY_0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
CREATED = DAY_0 - timedelta(days=5)


def _day(day: int) -> datetime:
    return DAY_0 + timedelta(days=day)


def _reminder(reminder_id: int, *, deleted_at: datetime | None = DAY_0, created_at: datetime = CREATED) -> Reminder:
    return Reminder(
        id=reminder_id, content="feed the cat", user_id=3, timestamp=DAY_0, created_at=created_at, deleted_at=deleted_at
    )


def _seed(engine: Engine, *rows: SQLModel) -> None:
    with Session(engine) as session:
        session.add_all(rows)
        session.commit()


def _cog(engine: Engine) -> Privacy:
    return detached_cog(Privacy, engine=engine)


def _created_at_after_storing_again(engine: Engine, reminder_id: int) -> datetime:
    """Store reminder ``reminder_id`` again with create_or_restore; return when the stored row was created."""
    with Session(engine) as session:
        stored = create_or_restore(session, _reminder(reminder_id, deleted_at=None, created_at=DAY_0))
        session.commit()
        return stored.created_at


async def test_a_reminder_deleted_29_days_ago_can_still_be_restored(engine: Engine) -> None:
    _seed(engine, _reminder(1))

    await _cog(engine).purge(_day(29))

    assert _created_at_after_storing_again(engine, 1) == CREATED  # restored, not new


async def test_a_reminder_deleted_31_days_ago_is_gone_for_good(engine: Engine) -> None:
    _seed(engine, _reminder(1))

    await _cog(engine).purge(_day(31))

    assert _created_at_after_storing_again(engine, 1) == DAY_0  # a fresh one


async def test_alive_reminders_are_never_purged(engine: Engine) -> None:
    _seed(engine, _reminder(1, deleted_at=None))

    await _cog(engine).purge(_day(10_000))

    with Session(engine) as session:
        assert [reminder.id for reminder in session.exec(alive(Reminder))] == [1]


async def test_purging_twice_at_the_same_moment_gives_the_same_result(engine: Engine) -> None:
    _seed(engine, _reminder(1), _reminder(2, deleted_at=_day(20)), _reminder(3, deleted_at=None))
    cog = _cog(engine)

    await cog.purge(_day(31))
    await cog.purge(_day(31))

    with Session(engine) as session:
        remaining = {reminder.id: reminder.deleted_at for reminder in session.exec(select(Reminder))}
    assert remaining == {2: _day(20), 3: None}


@pytest.fixture
def foreign_keys_engine() -> Engine:
    """Return an in-memory sqlite engine enforcing foreign keys, as postgres does, with every table created."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _enforce_foreign_keys(connection: DBAPIConnection, _: ConnectionPoolEntry) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    return engine


async def test_a_row_that_fails_is_logged_and_the_others_are_still_purged(
    foreign_keys_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sale = SteamSale(
        id=10,
        title="Game",
        url="https://store.steampowered.com/app/10/",
        sale_percent=100,
        final_price=0.0,
        update_datetime=DAY_0,
        discovered_at=DAY_0,
        deleted_at=DAY_0,
    )
    still_pointing = SteamSaleProperties(steam_sale_id=10, property=SaleTypes.DLC)  # alive: the sale can't go
    _seed(foreign_keys_engine, sale, still_pointing, _reminder(1))

    cog = _cog(foreign_keys_engine)
    cog.logger.addHandler(caplog.handler)

    try:
        with caplog.at_level(logging.WARNING):
            await cog.purge(_day(31))
    finally:
        cog.logger.removeHandler(caplog.handler)

    assert "Could not purge SteamSale 10" in caplog.text
    assert _created_at_after_storing_again(foreign_keys_engine, 1) == DAY_0  # the reminder went anyway


async def test_load_starts_the_daily_task_and_unload_cancels_it(engine: Engine) -> None:
    cog = detached_cog(Privacy, engine=engine, loop=asyncio.get_running_loop())
    cog._auto_reloader = cast("AutoReloadWatcher", SimpleNamespace(deregister=lambda: None))  # noqa: SLF001 - what __init__ sets up

    await cog.load()
    task = cog._task  # noqa: SLF001 - the task the cog owns
    assert task is not None
    await asyncio.sleep(0)
    assert not task.done()

    await cog.unload()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cog._task is None  # noqa: SLF001
