"""Run the archive: ``uv run python -m archive [--database-url URL]``.

Applies the database migrations, then records every gateway event until interrupted: each frame goes to the log
file (``logs/ArchiveGateway.log``) and, through the writer, to the database. The token is ``bot.ini``'s
``read_only_token``, or ``discord_token`` when that is empty; the other settings are in ``archive.ini``.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import TYPE_CHECKING

from herogold.log import LoggerMixin
from sqlalchemy import create_engine
from wd_bot.settings import Tokens
from wd_core.intents import Intents
from wd_core.sentry import Sentry

from archive.cleanup import RawEventPurge
from archive.gateway import ArchiveGateway
from archive.settings import ArchiveSettings
from archive.writer import Writer
from winter_dragon.migrations.__main__ import main as migrations


if TYPE_CHECKING:
    from sqlalchemy import Engine


def parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    root = argparse.ArgumentParser(prog="python -m archive", description=__doc__)
    root.add_argument("--database-url", help="database URL; defaults to the one database.ini configures")
    return root


def token() -> str:
    """Return the archive's token: the read-only one, or the bot's own when none is set."""
    return Tokens.read_only_token or Tokens.discord_token


async def archive(engine: Engine) -> None:
    """Record events into ``engine``'s database until cancelled or the gateway closes for good."""
    writer = Writer(
        engine,
        queue_limit=ArchiveSettings.queue_limit,
        batch_size=ArchiveSettings.batch_size,
        batch_interval=ArchiveSettings.batch_interval,
    )
    purge = RawEventPurge(engine, retention_days=ArchiveSettings.raw_event_retention_days)
    gateway = ArchiveGateway(token(), intents=Intents(ArchiveSettings.intents), writer=writer)
    gateway.capture_model_warnings()
    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(writer.run())
        tasks.create_task(purge.run())
        await gateway.connect()
        try:
            await gateway.run(gateway.archive)
        finally:
            await gateway.close()


def main(argv: list[str] | None = None) -> int:
    """Migrate the database, then run the archive; return the exit code."""
    url = parser().parse_args(argv).database_url
    LoggerMixin.set_log_directory("logs")
    if (failed := migrations(["--url", url, "upgrade"] if url else ["upgrade"])) != 0:
        return failed
    if url:
        engine = create_engine(url)
    else:
        from wd_db.constants import engine  # noqa: PLC0415 - builds the configured engine on import
    Sentry()
    asyncio.run(archive(engine))
    return 0


if __name__ == "__main__":
    sys.exit(main())
