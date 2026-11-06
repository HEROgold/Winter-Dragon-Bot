"""The dashboard's FastAPI app: its pages, the session cookie they share, and where a page that needs sign-in sends you."""

lazy from contextlib import asynccontextmanager
lazy from datetime import timedelta
lazy from typing import TYPE_CHECKING

lazy from fastapi import FastAPI, status
lazy from fastapi.responses import RedirectResponse
lazy from fastapi.staticfiles import StaticFiles
lazy from starlette.middleware.sessions import SessionMiddleware
lazy from starlette.responses import Response

lazy from winter_dragon.cogs import import_cogs
lazy from winter_dragon.metrics import observe_requests
lazy from winter_dragon.web import auth, bot_status, cards, pages, profile, redirect
lazy from winter_dragon.web.accounts import SignInRequired
lazy from winter_dragon.web.records import create_dashboard_tables
lazy from winter_dragon.web.responses import STATIC_DIR, is_htmx
lazy from winter_dragon.web.shared_guilds import SharedGuilds


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy import Engine
    from starlette.requests import Request

    from winter_dragon.web.discord_lookup import DiscordLookup


SESSION_COOKIE = "wd_session"


def create_app(
    *,
    bind: Engine,
    session_secret: str,
    session_lifetime: timedelta = timedelta(days=14),
    https_only: bool = False,
    lookup: DiscordLookup | None = None,
) -> FastAPI:
    """Return the dashboard on the database ``bind``, its session cookie signed with ``session_secret``.

    ``lookup`` names the Discord IDs its pages show and is opened while the app runs; without one they show as plain IDs.

    Imports every cog first, so the data page knows each table the bot stores, and creates the tables it writes to.
    """
    import_cogs()
    create_dashboard_tables(bind)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if lookup is None:
            yield
            return
        async with lookup:
            yield

    app = FastAPI(title="Winter Dragon", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.bind = bind
    app.state.lookup = lookup
    app.state.shared_guilds = SharedGuilds()
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        session_cookie=SESSION_COOKIE,
        max_age=int(session_lifetime.total_seconds()),
        same_site="lax",
        https_only=https_only,
    )
    observe_requests(app)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    for router in (pages.router, auth.router, profile.router, cards.router, bot_status.router, redirect.router):
        app.include_router(router)
    for page in profile.profile_pages():
        if page.router is not None:
            app.include_router(page.router, prefix=page.path)
    app.add_exception_handler(SignInRequired, _to_sign_in)
    return app


def _to_sign_in(request: Request, _: Exception) -> Response:
    """Send a visitor who isn't signed in to sign in; htmx follows the ``HX-Redirect`` header instead of a 303."""
    if is_htmx(request):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED, headers={"HX-Redirect": auth.LOGIN_PATH})
    return RedirectResponse(auth.LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
