"""Print an archive report: ``uv run python -m archive.reports {changing-fields,unmodelled} [--database-url URL]``.

Both reports read the raw events (the last 30 days, by default), in the order they were received.
"""

import argparse
import sys
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine
from sqlmodel import Session, col, select

from archive.models import GatewayEvent
from archive.reports import changing_fields, unmodelled


if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from sqlalchemy import Engine


def parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    root = argparse.ArgumentParser(prog="python -m archive.reports", description=__doc__)
    root.add_argument("--database-url", help="database URL; defaults to the one database.ini configures")
    reports = root.add_subparsers(dest="report", required=True)
    changes = reports.add_parser("changing-fields", help="which fields of which objects change most often")
    changes.add_argument("--limit", type=int, default=50, help="how many fields to list")
    reports.add_parser("unmodelled", help="events without a wd-discord model, and fields models don't know")
    return root


def raw_events(engine: Engine) -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Yield every raw event as (name, payload), oldest first."""
    with Session(engine) as session:
        statement = (
            select(GatewayEvent.name, GatewayEvent.payload).order_by(col(GatewayEvent.id)).execution_options(yield_per=500)
        )
        for name, payload in session.exec(statement):
            yield name, payload or {}


def main(argv: list[str] | None = None) -> int:
    """Print the report ``argv`` asks for; return the exit code."""
    args = parser().parse_args(argv)
    if args.database_url:
        engine = create_engine(args.database_url)
    else:
        from wd_db.constants import engine  # noqa: PLC0415 - builds the configured engine on import
    if args.report == "changing-fields":
        print(changing_fields.render(changing_fields.count_changes(raw_events(engine)), limit=args.limit))
    else:
        print(unmodelled.render(unmodelled.find_unmodelled(raw_events(engine))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
