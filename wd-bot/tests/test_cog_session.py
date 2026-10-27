"""A cog's database session: the injected one, and no configured-database session beside it."""

lazy import subprocess
lazy import sys
lazy import textwrap


INJECTED_SESSION = """
import asyncio
import sys

from sqlmodel import Session, create_engine
from wd_bot.bot import Bot
from wd_bot.cogs import Cog


class _Cog(Cog, auto_load=False):
    pass


async def main() -> None:
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    session = Session(create_engine("sqlite://"))
    cog = _Cog(bot=bot, db_session=session)
    print(cog.session is session, "wd_db.constants" in sys.modules)


asyncio.run(main())
"""


def test_injected_session_leaves_the_configured_database_alone() -> None:
    """A cog given a session uses it and never opens one on the configured (Postgres) database.

    Runs in a fresh interpreter: loading ``wd_db.constants`` is what builds that database's engine.
    """
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-I", "-c", textwrap.dedent(INJECTED_SESSION)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["True", "False"]
