"""Signing in with Discord and out again; the callback sets the HttpOnly session cookie, never a token."""

lazy import secrets

from fastapi import APIRouter, Depends
lazy from fastapi import Request, status
lazy from fastapi.responses import RedirectResponse
lazy from starlette.responses import Response

lazy from winter_dragon.web.accounts import STATE_KEY, Account, checked_csrf, sign_in, sign_out
lazy from winter_dragon.web.discord_oauth import CALLBACK_PATH, authorization_url, signed_in_user
lazy from winter_dragon.web.responses import render, see_other


router = APIRouter()

LOGIN_PATH = "/auth/discord/login"


@router.get(LOGIN_PATH)
def login(request: Request) -> Response:
    """Send the visitor to Discord to sign in, remembering the ``state`` the callback must bring back."""
    state = request.session[STATE_KEY] = secrets.token_urlsafe(32)
    return RedirectResponse(authorization_url(state), status_code=status.HTTP_302_FOUND)


@router.get(CALLBACK_PATH)
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    """Finish signing in with the ``code`` Discord sent back, if its ``state`` is the one this session asked for."""
    expected = request.session.pop(STATE_KEY, None)
    if error is not None or code is None or state is None or expected is None or not secrets.compare_digest(state, expected):
        message = "Signing in was cancelled, or took too long. Try again."
        return render(request, "error.html", status_code=status.HTTP_400_BAD_REQUEST, message=message)
    user = await signed_in_user(code)
    if user is None:
        message = "Discord didn't let us sign you in. Try again in a moment."
        return render(request, "error.html", status_code=status.HTTP_502_BAD_GATEWAY, message=message)
    sign_in(request, Account.from_user(user))
    return see_other("/me")


@router.post("/auth/logout", dependencies=[Depends(checked_csrf)])
def logout(request: Request) -> Response:
    """Sign out, and go back to the landing page."""
    sign_out(request)
    return see_other("/")
