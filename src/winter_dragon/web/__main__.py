"""Serve the dashboard: uv run python -m winter_dragon.web.

Shares the bot's database and ini files; the dashboard's own settings are in ``dashboard.ini``.
"""

lazy import asyncio
lazy import sys
lazy from datetime import timedelta

from wd_discord import Sentry
lazy import uvicorn
lazy from herogold import log
lazy from wd_bot.application import ApplicationId, ApplicationOwners
lazy from wd_bot.settings import Tokens
lazy from wd_config.parser import OperatorFiles
lazy from wd_db.constants import engine
lazy from wd_discord import Client, Token

from winter_dragon.web.settings import DashboardSettings
lazy from winter_dragon.cogs import import_cogs
lazy from winter_dragon.metrics import Exporter
lazy from winter_dragon.web.app import create_app


async def _load_application() -> None:
    """Ask Discord which application the bot token belongs to and who owns it.

    Sign-in and the invite link need its ID; the owners' pages need its owners.
    """
    async with Client(Token(Tokens.discord_token)) as client:
        await ApplicationId.load(client)
        await ApplicationOwners.load(client)


def main() -> None:
    """Check the operator files, learn the application ID and owners, then serve the dashboard and its metrics."""
    # dashboard.ini is registered on import; importing the cogs registers config.ini and cogs.ini, so the check
    # covers every file the pages read.
    log.setup()
    import_cogs()
    OperatorFiles.check()
    Sentry()
    asyncio.run(_load_application())
    Exporter.serve()
    app = create_app(
        bind=engine,
        session_secret=DashboardSettings.session_secret,
        session_lifetime=timedelta(days=DashboardSettings.session_days),
        https_only=DashboardSettings.https_only(),
    )
    uvicorn.run(app, host=DashboardSettings.host, port=DashboardSettings.port, proxy_headers=True)


if __name__ == "__main__":
    sys.exit(main())
