"""Serve the dashboard: uv run python -m winter_dragon.web.

Shares the bot's database and ini files; the dashboard's own settings are in ``dashboard.ini``.
"""

lazy import asyncio
lazy import sys
lazy from datetime import timedelta

from wd_core.sentry import Sentry
lazy import uvicorn
lazy from wd_bot.application import ApplicationId
lazy from wd_bot.settings import Tokens
lazy from wd_config.parser import OperatorFiles
lazy from wd_db.constants import engine
lazy from wd_discord import Client

from winter_dragon.web.settings import DashboardSettings
lazy from winter_dragon.cogs import import_cogs
lazy from winter_dragon.web.app import create_app


async def _load_application_id() -> None:
    """Ask Discord which application the bot token belongs to; sign-in and the invite link need its ID."""
    async with Client(Tokens.discord_token) as client:
        await ApplicationId.load(client)


def main() -> None:
    """Check every operator file is filled in, learn the application ID, then serve the dashboard until stopped."""
    # dashboard.ini is registered on import; importing the cogs registers config.ini and cogs.ini, so the check
    # covers every file the pages read.
    import_cogs()
    OperatorFiles.check()
    Sentry()
    asyncio.run(_load_application_id())
    app = create_app(
        bind=engine,
        session_secret=DashboardSettings.session_secret,
        session_lifetime=timedelta(days=DashboardSettings.session_days),
        https_only=DashboardSettings.https_only(),
    )
    uvicorn.run(app, host=DashboardSettings.host, port=DashboardSettings.port, proxy_headers=True)


if __name__ == "__main__":
    sys.exit(main())
