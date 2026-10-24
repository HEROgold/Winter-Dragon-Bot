"""The archive's single database writer: a bounded queue of jobs, written in batches by one task.

Receiving events never waits on the database: the gateway only queues jobs (:meth:`Writer.put`). The writer runs
each batch in a worker thread with its one session, each job in a savepoint, so a job that fails (a payload the
tables can't take) is logged and skipped without losing the rest. When the database itself fails, the batch is
rolled back and retried with backoff; meanwhile the queue fills, and once full, new jobs are dropped and counted.
"""

import asyncio
from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING

import sentry_sdk
from herogold.log import LoggerMixin
from sqlalchemy.exc import OperationalError
from sqlmodel import Session


if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import Engine


type Job = Callable[[Session], None]
"""One write, run inside the writer's session."""


@dataclass
class Writer(LoggerMixin):
    """Queues jobs and writes them to ``engine`` in batches."""

    engine: Engine
    _: KW_ONLY
    queue_limit: int = 50_000
    """Jobs the queue holds before new ones are dropped."""
    batch_size: int = 200
    """Most jobs written per transaction."""
    batch_interval: float = 0.5
    """Seconds a batch waits to fill up before it is written anyway."""
    max_backoff: float = 60.0
    """Longest wait, in seconds, between retries of a batch the database refused."""
    queue: asyncio.Queue[Job] = field(init=False)
    dropped: int = field(default=0, init=False)
    """Jobs dropped since the last report."""

    def __post_init__(self) -> None:
        """Create the bounded queue."""
        self.queue = asyncio.Queue(self.queue_limit)

    def put(self, job: Job) -> None:
        """Queue ``job``; when the queue is full, drop it and count it."""
        try:
            self.queue.put_nowait(job)
        except asyncio.QueueFull:
            self.dropped += 1

    async def run(self) -> None:
        """Write batches until cancelled; on cancel, write what is still queued first."""
        with Session(self.engine) as session:
            try:
                while True:
                    batch = await self._next_batch()
                    await self._write_until_stored(session, batch)
                    self._report_dropped()
            except asyncio.CancelledError:
                self.write(session, self._drain())
                raise

    def write(self, session: Session, batch: list[Job]) -> None:
        """Run ``batch`` in ``session`` and commit; a job that fails is logged and skipped.

        Raises:
            OperationalError: the database failed; the batch is rolled back.

        """
        try:
            for job in batch:
                self._run_job(session, job)
            session.commit()
        except OperationalError:
            session.rollback()
            raise
        finally:
            session.expunge_all()

    def _run_job(self, session: Session, job: Job) -> None:
        """Run ``job`` in a savepoint, so its failure undoes only its own writes."""
        try:
            with session.begin_nested():
                job(session)
        except OperationalError:
            raise
        except Exception as error:
            self.logger.exception(t"Skipped an archive write.")
            sentry_sdk.capture_exception(error)

    async def _next_batch(self) -> list[Job]:
        """Wait for a job, then gather more for up to :attr:`batch_interval` seconds or :attr:`batch_size` jobs."""
        batch = [await self.queue.get()]
        deadline = asyncio.get_running_loop().time() + self.batch_interval
        while len(batch) < self.batch_size:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            try:
                batch.append(await asyncio.wait_for(self.queue.get(), remaining))
            except TimeoutError:
                break
        return batch

    async def _write_until_stored(self, session: Session, batch: list[Job]) -> None:
        """Write ``batch``, retrying with doubling backoff while the database fails."""
        backoff = 1.0
        while True:
            try:
                await asyncio.to_thread(self.write, session, batch)
            except OperationalError as error:
                self.logger.warning(t"Database unavailable, retrying in {backoff:.0f}s: {error!r}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff)
            else:
                return

    def _drain(self) -> list[Job]:
        """Take every job still queued."""
        jobs = []
        while not self.queue.empty():
            jobs.append(self.queue.get_nowait())
        return jobs

    def _report_dropped(self) -> None:
        """Log and report the jobs dropped since the last report."""
        if not self.dropped:
            return
        self.logger.warning(t"Queue full: dropped {self.dropped} archive writes (the log file still has the events).")
        sentry_sdk.capture_message(f"archive: dropped {self.dropped} writes, queue full", level="warning")
        self.dropped = 0
