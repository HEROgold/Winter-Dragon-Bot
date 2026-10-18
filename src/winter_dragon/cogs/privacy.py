"""Privacy: soft-deleted records are purged for good once they've been deleted for :data:`RETENTION`.

Deleting a record only soft-deletes it, so it can still be restored for a while. Once a day this cog hard-deletes
every soft-deleted row of every lifecycle table older than that, so "deleted" turns into "gone" on schedule.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
lazy import asyncio
lazy from typing import TYPE_CHECKING, override

lazy from sqlalchemy import inspect
lazy from sqlalchemy.exc import SQLAlchemyError
lazy from sqlmodel import Session, SQLModel, col, select
lazy from wd_bot.cogs import Cog
lazy from wd_db.extension.lifecycle import lifecycle_models


if TYPE_CHECKING:
    lazy from collections.abc import Iterable

    lazy from wd_db.extension.lifecycle import LifecycleModel


RETENTION = timedelta(days=30)
"""How long a soft-deleted record can still be restored before it's purged for good."""
PURGE_INTERVAL = timedelta(days=1)
"""How often the purge runs."""


def purge_order(models: Iterable[type[LifecycleModel]]) -> list[type[LifecycleModel]]:
    """Return ``models`` children first: a table that points at another (by foreign key) comes before it."""
    rank = {table.name: index for index, table in enumerate(SQLModel.metadata.sorted_tables)}
    return sorted(models, key=lambda model: rank[model.__table__.name], reverse=True)


class Privacy(Cog):
    """Purges soft-deleted records older than :data:`RETENTION` once a day, from a background task."""

    _task: asyncio.Task[None] | None = None

    @override
    async def load(self) -> None:
        """Start the background task purging soft-deleted records."""
        self._task = self.bot.loop.create_task(self._run())

    @override
    async def unload(self) -> None:
        """Stop the background task."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        await super().unload()

    async def _run(self) -> None:
        """Purge every :data:`PURGE_INTERVAL`, forever; a failing pass is logged and the next one runs as usual."""
        while True:
            try:
                await self.purge(datetime.now(UTC))
            except Exception:
                self.logger.exception(t"Purging soft-deleted records failed")
            await asyncio.sleep(PURGE_INTERVAL.total_seconds())

    async def purge(self, now: datetime) -> None:
        """Hard-delete every lifecycle row soft-deleted more than :data:`RETENTION` before ``now``, children first.

        Each row is deleted on its own, so one that fails (a row still pointing at it, say) is logged and skipped
        while the rest go. Running it again at the same ``now`` deletes nothing more.
        """
        cutoff = now - RETENTION
        existing = set(inspect(self.bind).get_table_names())
        for model in purge_order(lifecycle_models()):
            if model.__table__.name in existing:
                self._purge_table(model, cutoff)

    def _purge_table(self, model: type[LifecycleModel], cutoff: datetime) -> None:
        """Hard-delete ``model``'s rows soft-deleted before ``cutoff``, one at a time."""
        with Session(self.bind) as session:
            expired = session.exec(select(model.id).where(col(model.deleted_at) < cutoff)).all()
        for row_id in expired:
            with Session(self.bind) as session:
                row = session.get(model, row_id)
                if row is None:
                    continue
                session.delete(row)
                try:
                    session.commit()
                except SQLAlchemyError as error:
                    self.logger.warning(t"Could not purge {model.__name__} {row_id}: {error}")
