"""OAuth2: scopes, and the authorization code grant's exchange and revoke (https://docs.discord.com/developers/topics/oauth2).

The exchange and revoke go through a :class:`~wd_discord.client.Client` that authenticates as the application, one
built with :func:`~wd_discord.authenticate.client_credentials` and ``TokenType.BASIC``. They return a failure as a
value, like every other REST call.
"""

lazy from enum import StrEnum
lazy from typing import TYPE_CHECKING

from wd_discord.authenticate import Token
from wd_discord.models import DiscordModel
lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import parse


if TYPE_CHECKING:
    from wd_discord.authenticate import URL
    from wd_discord.client import Client, NetworkError


class OAuthScopes(StrEnum):
    """OAuth2 Scopes for the User Object.

    https://docs.discord.com/developers/topics/oauth2#shared-resources-oauth2-scopes
    """

    IDENTIFY = "identify"
    EMAIL = "email"
    PREMIUM = "premium"

    def __or__(self, other: OAuthScopes | str) -> str:
        """Return the combination of two AuthScopes."""
        match other:
            case OAuthScopes():
                return f"{self.value}.{other.value}"
            case str():
                return f"{self.value}.{other}"


class AccessToken(DiscordModel):
    """The token response of the code grant (https://docs.discord.com/developers/topics/oauth2#authorization-code-grant-access-token-response)."""

    access_token: Token
    token_type: str
    expires_in: int
    scope: str
    refresh_token: Token | None = None


async def exchange_code(client: Client, code: str, redirect_uri: URL) -> AccessToken | NetworkError:
    """POST /oauth2/token - trade the ``code`` a user authorized with for an access token.

    ``client`` must authenticate as the application; ``redirect_uri`` must be the one the authorization used.
    """
    grant = {"grant_type": "authorization_code", "code": code, "redirect_uri": str(redirect_uri)}
    return parse(await client.post(t"/oauth2/token", data=grant), AccessToken)


async def revoke_token(client: Client, token: Token) -> NetworkError | None:
    """POST /oauth2/token/revoke - revoke the access ``token``; ``client`` must authenticate as the application."""
    revoke = {"token": str(token), "token_type_hint": "access_token"}
    result = await client.post(t"/oauth2/token/revoke", data=revoke)
    return result if is_network_error(result) else None
