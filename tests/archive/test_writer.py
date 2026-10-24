"""The writer batches jobs, skips a failing one, drops when full; the purge removes only old raw events."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select
from wd_types.clock import utc_now

from archive import models as db
from archive.cleanup import RawEventPurge
from archive.writer import Job, Writer


if TYPE_CHECKING:
    from sqlalchemy import Engine


def add_user(user_id: int) -> Job:
    def job(session: Session) -> None:
        session.add(db.User(id=user_id, username=f"user{user_id}"))

    return job


def fail(_session: Session) -> None:
    msg = "a payload the tables can't take"
    raise ValueError(msg)


def user_ids(engine: Engine) -> list[int]:
    with Session(engine) as session:
        return sorted(user.id for user in session.exec(select(db.User)))


def test_a_failing_job_is_skipped_and_the_rest_are_written(engine: Engine) -> None:
    writer = Writer(engine)
    with Session(engine) as session:
        writer.write(session, [add_user(1), fail, add_user(2)])

    assert user_ids(engine) == [1, 2]


def test_a_database_failure_rolls_the_batch_back(engine: Engine) -> None:
    def database_down(_session: Session) -> None:
        msg = "SELECT 1"
        raise OperationalError(msg, {}, Exception("connection refused"))

    writer = Writer(engine)
    with Session(engine) as session, contextlib.suppress(OperationalError):
        writer.write(session, [add_user(1), database_down])

    assert user_ids(engine) == []


def test_a_full_queue_drops_and_counts(engine: Engine) -> None:
    async def scenario() -> Writer:
        writer = Writer(engine, queue_limit=2)
        for user_id in range(5):
            writer.put(add_user(user_id))
        return writer

    writer = asyncio.run(scenario())
    assert writer.queue.qsize() == 2
    assert writer.dropped == 3


def test_run_writes_queued_jobs_in_batches(engine: Engine) -> None:
    async def scenario() -> None:
        writer = Writer(engine, batch_size=2, batch_interval=0.01)
        task = asyncio.create_task(writer.run())
        for user_id in range(5):
            writer.put(add_user(user_id))
        while writer.queue.qsize():
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())
    assert user_ids(engine) == [0, 1, 2, 3, 4]


def test_purge_removes_only_raw_events_past_retention(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(db.GatewayEvent(name="OLD", created_at=utc_now() - timedelta(days=31)))
        session.add(db.GatewayEvent(name="NEW", created_at=utc_now() - timedelta(days=29)))
        session.commit()

    assert RawEventPurge(engine, retention_days=30).purge() == 1
    with Session(engine) as session:
        assert [event.name for event in session.exec(select(db.GatewayEvent))] == ["NEW"]
