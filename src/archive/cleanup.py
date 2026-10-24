"""The archive's daily task: purge raw events older than the retention period."""

import asyncio
from dataclasses import KW_ONLY, dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from herogold.log import LoggerMixin
from sqlmodel import Session, col, delete
from wd_types.clock import utc_now

from archive.models import GatewayEvent


if TYPE_CHECKING:
    from sqlalchemy import Engine


DAY = 24 * 60 * 60


@dataclass
class RawEventPurge(LoggerMixin):
    """Deletes raw events older than :attr:`retention_days`, once a day."""

    engine: Engine
    _: KW_ONLY
    retention_days: int = 30

    async def run(self) -> None:
        """Purge now, then once a day, until cancelled."""
        while True:
            deleted = await asyncio.to_thread(self.purge)
            self.logger.info(t"Purged {deleted} raw events older than {self.retention_days} days.")
            await asyncio.sleep(DAY)

    def purge(self) -> int:
        """Delete the raw events older than :attr:`retention_days`; return how many."""
        cutoff = utc_now() - timedelta(days=self.retention_days)
        with Session(self.engine) as session:
            result = session.exec(delete(GatewayEvent).where(col(GatewayEvent.created_at) < cutoff))
            session.commit()
        return result.rowcount
