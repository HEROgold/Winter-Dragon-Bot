"""Signing in with Discord and out again; the callback sets the HttpOnly session cookie, never a token."""

lazy import secrets

from fastapi import APIRouter, Depends
lazy from fastapi import Request, status
lazy from fastapi.responses import RedirectResponse
lazy from starlette.responses import Response

lazy from winter_dragon.web.accounts import (
    NEXT_KEY,
    SILENT_KEY,
    STATE_KEY,
    Account,
    checked_csrf,
    session_id,
    sign_in,
    sign_out,
)
lazy from winter_dragon.web.discord_oauth import CALLBACK_PATH, authorization_url, signed_in_user
lazy from winter_dragon.web.responses import render, see_other
lazy from winter_dragon.web.shared_guilds import safe_return_path


router = APIRouter()

LOGIN_PATH = "/auth/discord/login"
RETRY_ERRORS = frozenset({"consent_required", "interaction_required", "login_required"})
"""What Discord answers a silent (``prompt=none``) request that needs the member to act."""


def _to_discord(request: Request, *, silent: bool) -> Response:
    """Send the visitor to Discord, remembering the ``state`` the callback must bring back."""
    state = request.session[STATE_KEY] = secrets.token_urlsafe(32)
    request.session[SILENT_KEY] = silent
    return RedirectResponse(authorization_url(state, silent=silent), status_code=status.HTTP_302_FOUND)


@router.get(LOGIN_PATH)
def login(request: Request, next: str | None = None) -> Response:  # noqa: A002 - the query parameter's name
    """Send the visitor to Discord to sign in, then back to ``next`` when that is a page of this site.

    Asks Discord silently first: a member who approved the dashboard before comes straight back.
    """
    return_to = safe_return_path(next)
    if return_to is not None:
        request.session[NEXT_KEY] = return_to
    else:
        request.session.pop(NEXT_KEY, None)
    return _to_discord(request, silent=True)


@router.get(CALLBACK_PATH)
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    """Finish signing in with the ``code`` Discord sent back, if its ``state`` is the one this session asked for."""
    expected = request.session.pop(STATE_KEY, None)
    was_silent = bool(request.session.pop(SILENT_KEY, False))
    state_matches = state is not None and expected is not None and secrets.compare_digest(state, expected)
    if state_matches and was_silent and error in RETRY_ERRORS:
        return _to_discord(request, silent=False)
    if error is not None or code is None or not state_matches:
        message = "Signing in was cancelled, or took too long. Try again."
        return render(request, "error.html", status_code=status.HTTP_400_BAD_REQUEST, message=message)
    granted = await signed_in_user(code)
    if granted is None:
        message = "Discord didn't let us sign you in. Try again in a moment."
        return render(request, "error.html", status_code=status.HTTP_502_BAD_GATEWAY, message=message)
    return_to = safe_return_path(request.session.get(NEXT_KEY)) or "/me"
    sign_in(request, Account.from_user(granted.user))
    lookup = request.app.state.lookup
    session = session_id(request)
    if lookup is not None and session is not None:
        # When Discord can't list the bot's guilds, no card opens until the guilds are read again.
        bot_guilds = await lookup.bot_guild_ids() or frozenset()
        request.app.state.shared_guilds.remember(session, granted.guild_ids & bot_guilds)
    return see_other(return_to)


@router.post("/auth/logout", dependencies=[Depends(checked_csrf)])
def logout(request: Request) -> Response:
    """Sign out, and go back to the landing page."""
    request.app.state.shared_guilds.forget(session_id(request))
    sign_out(request)
    return see_other("/")
