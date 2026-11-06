"""Signing in with Discord: the OAuth2 authorization code grant, used only to learn who is signing in.

The access token is revoked as soon as the user and their guilds are known; the dashboard keeps nothing but the
signed-in account in its session cookie (https://docs.discord.com/developers/topics/oauth2#authorization-code-grant).
The guilds are only used to decide which cards the member may open, and live in memory (ADR 0006).
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING
lazy from urllib.parse import urlencode

from wd_discord.authenticate import URL
lazy from wd_bot.application import ApplicationId
lazy from wd_config.discord import URLS
lazy from wd_discord import Client, Token, TokenType, is_network_error
lazy from wd_discord.authenticate import client_credentials
lazy from wd_discord.log import get_logger
lazy from wd_discord.oauth import OAuthScopes, exchange_code, revoke_token

lazy from winter_dragon.web.settings import DashboardSettings


if TYPE_CHECKING:
    from wd_discord.resources.user.user import User
    from wd_discord.snowflake import Snowflake


CALLBACK_PATH = "/auth/discord/callback"
"""Where Discord sends the browser back to after the user authorizes the dashboard."""

SCOPES = f"{OAuthScopes.IDENTIFY} {OAuthScopes.GUILDS}"
"""What the dashboard asks for: who the member is, and which guilds they are in."""

logger = get_logger(__name__)


@dataclass(frozen=True)
class Granted:
    """What signing in learned: the member, and every guild they are in (empty if Discord wouldn't say)."""

    user: User
    guild_ids: frozenset[Snowflake]


def redirect_uri() -> URL:
    """Return the callback URL Discord redirects to, under :attr:`DashboardSettings.public_url`."""
    return URL(f"{DashboardSettings.public_url.rstrip('/')}{CALLBACK_PATH}")


def authorization_url(state: str, *, silent: bool = True) -> URL:
    """Return the Discord page asking the user to sign in, which sends ``state`` back to the callback.

    A ``silent`` request (``prompt=none``) skips the consent page for a member who already approved the dashboard, and
    comes back with an error otherwise.
    """
    query = urlencode(
        {
            "response_type": "code",
            "client_id": ApplicationId.get(),
            "scope": SCOPES,
            "state": state,
            "redirect_uri": redirect_uri(),
            "prompt": "none" if silent else "consent",
        },
    )
    return URL(f"{URLS().oauth2_authorize}?{query}")


async def signed_in_user(code: str) -> Granted | None:
    """Return the Discord user who authorized the dashboard with ``code``, and their guilds; ``None`` when Discord refused it.

    Exchanges ``code`` for an access token, reads the user it belongs to and their guilds, then revokes the token.
    A failure to list the guilds still signs the member in, with no guilds.
    """
    credentials = client_credentials(ApplicationId.get(), Token(DashboardSettings.client_secret))
    async with Client(credentials, token_type=TokenType.BASIC) as application:
        granted = await exchange_code(application, code, redirect_uri())
        if is_network_error(granted):
            logger.warning(t"Discord refused the OAuth2 code exchange: {granted}")
            return None
        async with Client(granted.access_token, token_type=TokenType.BEARER) as user:
            me = await user.users.me()
            guilds = await user.users.guilds()
        await revoke_token(application, granted.access_token)
    if is_network_error(me):
        return None
    if is_network_error(guilds):
        logger.warning(t"Couldn't read the guilds of {me.id} while signing in: {guilds}")
        return Granted(me.model, frozenset())
    return Granted(me.model, frozenset(guild.id for guild in guilds))
