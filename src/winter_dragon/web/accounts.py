"""Who is signed in to the dashboard, kept in the signed session cookie, and the CSRF token their forms carry."""

lazy import secrets
lazy from functools import cache
lazy from typing import TYPE_CHECKING, Annotated, Self

from fastapi import Depends
from pydantic import BaseModel, ConfigDict
lazy from fastapi import HTTPException, Request, status
lazy from zoneinfo import ZoneInfo, available_timezones


if TYPE_CHECKING:
    from wd_discord.resources.user.user import User


ACCOUNT_KEY = "account"
"""The session key holding the signed-in :class:`Account`."""
CSRF_KEY = "csrf"
"""The session key holding the token every state-changing form must send back."""
STATE_KEY = "oauth_state"
"""The session key holding the OAuth2 ``state`` of a sign-in in progress."""
CSRF_FIELD = "csrf_token"
"""The form field carrying the CSRF token."""
ZONE_COOKIE = "tz"
"""The cookie the browser sets to its IANA time zone, so times show in the visitor's own."""


class Account(BaseModel):
    """The Discord user signed in to the dashboard: only what its pages show of them."""

    model_config = ConfigDict(frozen=True)

    id: int
    username: str
    display_name: str
    avatar_url: str | None = None

    @classmethod
    def from_user(cls, user: User) -> Self:
        """Return the account of the Discord ``user``."""
        avatar = None if user.avatar is None else user.avatar.url(f"avatars/{user.id}")
        return cls(id=int(user.id), username=user.username, display_name=user.global_name or user.username, avatar_url=avatar)

    @property
    def initials(self) -> str:
        """The first two letters of the display name, shown when there is no avatar."""
        return self.display_name[:2].upper()


class SignInRequired(Exception):  # noqa: N818 - a redirect, not an error
    """A page that needs a signed-in account was opened without one."""


def current_account(request: Request) -> Account | None:
    """Return the account signed in on ``request``, if any."""
    stored = request.session.get(ACCOUNT_KEY)
    return None if stored is None else Account.model_validate(stored)


def signed_in(request: Request) -> Account:
    """Return the signed-in account; the FastAPI dependency of every page that needs one.

    Raises:
        SignInRequired: no one is signed in.

    """
    account = current_account(request)
    if account is None:
        raise SignInRequired
    return account


SignedIn = Annotated[Account, Depends(signed_in)]
"""The signed-in account, as a route parameter's annotation; a visitor who isn't signed in is sent to sign in."""


def sign_in(request: Request, account: Account) -> None:
    """Start a fresh session for ``account``, dropping whatever the old one held."""
    request.session.clear()
    request.session[ACCOUNT_KEY] = account.model_dump()


def sign_out(request: Request) -> None:
    """End the session on ``request``."""
    request.session.clear()


def csrf_token(request: Request) -> str:
    """Return the session's CSRF token, creating it on first use."""
    token = request.session.get(CSRF_KEY)
    if token is None:
        token = request.session[CSRF_KEY] = secrets.token_urlsafe(32)
    return token


async def checked_csrf(request: Request) -> None:
    """Refuse a state-changing request whose form doesn't carry the session's CSRF token; a FastAPI dependency.

    Raises:
        HTTPException: 403, the token is missing or wrong.

    """
    sent = (await request.form()).get(CSRF_FIELD)
    expected = request.session.get(CSRF_KEY)
    if not isinstance(sent, str) or expected is None or not secrets.compare_digest(sent, expected):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This form expired. Reload the page and try again.")


@cache
def _zone_names() -> frozenset[str]:
    return frozenset(available_timezones())


def visitor_zone(request: Request) -> ZoneInfo:
    """Return the time zone the visitor's browser reported, or UTC until it has."""
    name = request.cookies.get(ZONE_COOKIE, "UTC")
    return ZoneInfo(name if name in _zone_names() else "UTC")
