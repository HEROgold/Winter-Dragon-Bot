"""Signing in with Discord: the OAuth2 authorization code grant, used only to learn who is signing in.

The access token is revoked as soon as the user is known; the dashboard keeps nothing but the signed-in account in
its session cookie (https://docs.discord.com/developers/topics/oauth2#authorization-code-grant).
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING
lazy from urllib.parse import urlencode

from wd_discord.models import DiscordModel
lazy from herogold.log import getLogger
lazy from httpxyz import AsyncClient, BasicAuth, RequestError
lazy from wd_bot.application import ApplicationId
lazy from wd_config.discord import URLS
lazy from wd_discord.oauth import OAuthScopes
lazy from wd_discord.resources.user.user import User

lazy from winter_dragon.web.settings import DashboardSettings


if TYPE_CHECKING:
    from httpxyz import Response


CALLBACK_PATH = "/auth/discord/callback"
"""Where Discord sends the browser back to after the user authorizes the dashboard."""
REQUEST_TIMEOUT = 10.0
"""Seconds a call to Discord's OAuth2 endpoints may take."""

logger = getLogger(__name__)


class AccessToken(DiscordModel):
    """The token response of the code grant (https://docs.discord.com/developers/topics/oauth2#authorization-code-grant-access-token-response)."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    refresh_token: str | None = None


def redirect_uri() -> str:
    """Return the callback URL Discord redirects to, under :attr:`DashboardSettings.public_url`."""
    return f"{DashboardSettings.public_url.rstrip('/')}{CALLBACK_PATH}"


def authorization_url(state: str) -> str:
    """Return the Discord page asking the user to sign in, which sends ``state`` back to the callback."""
    query = urlencode(
        {
            "response_type": "code",
            "client_id": ApplicationId.get(),
            "scope": OAuthScopes.IDENTIFY,
            "state": state,
            "redirect_uri": redirect_uri(),
            "prompt": "none",
        },
    )
    return f"{URLS().oauth2_authorize}?{query}"


def _api(path: str) -> str:
    urls = URLS()
    return f"{urls.base}/{urls.api_version}{path}"


async def _send(  # noqa: PLR0913 - one keyword per part of the request
    http: AsyncClient,
    method: str,
    path: str,
    *,
    data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    auth: BasicAuth | None = None,
) -> Response | None:
    """Send one request to Discord; ``None`` when it never got an answer, which is logged."""
    try:
        return await http.request(method, _api(path), data=data, headers=headers, auth=auth)
    except RequestError as error:
        logger.warning(t"Discord OAuth2 {method} {path} failed: {error}")
        return None


async def signed_in_user(code: str) -> User | None:
    """Return the Discord user who authorized the dashboard with ``code``; ``None`` when Discord refused it.

    Exchanges ``code`` for an access token, reads the user it belongs to, then revokes the token.
    """
    auth = BasicAuth(str(ApplicationId.get()), DashboardSettings.client_secret)
    grant = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri()}
    async with AsyncClient(timeout=REQUEST_TIMEOUT) as http:
        granted = await _send(http, "POST", "/oauth2/token", data=grant, auth=auth)
        if granted is None or not granted.is_success:
            return None
        token = AccessToken.model_validate(granted.json())
        me = await _send(http, "GET", "/users/@me", headers={"Authorization": f"Bearer {token.access_token}"})
        revoke = {"token": token.access_token, "token_type_hint": "access_token"}
        await _send(http, "POST", "/oauth2/token/revoke", data=revoke, auth=auth)
    if me is None or not me.is_success:
        return None
    return User.model_validate(me.json())
