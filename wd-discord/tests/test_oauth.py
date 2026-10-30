"""Unit tests: OAuth2 scopes, and the code exchange and token revoke over the recorded transport."""

lazy import pytest
lazy from wd_discord import ApiResponseError, Token
lazy from wd_discord.authenticate import URL
lazy from wd_discord.oauth import AccessToken, OAuthScopes, exchange_code, revoke_token
lazy from wd_discord.testing import RecordingClient


def test_scope_values() -> None:
    assert OAuthScopes.IDENTIFY == "identify"
    assert OAuthScopes.EMAIL == "email"
    assert OAuthScopes.PREMIUM == "premium"


def test_or_combines_two_scopes() -> None:
    assert OAuthScopes.IDENTIFY | OAuthScopes.EMAIL == "identify.email"


def test_or_combines_scope_and_str() -> None:
    assert OAuthScopes.IDENTIFY | "email" == "identify.email"


@pytest.mark.xfail(
    reason="__or__ has no default case: unknown types fall through to None instead of raising.",
    strict=True,
)
def test_or_rejects_unknown_type() -> None:
    with pytest.raises(TypeError):
        _ = OAuthScopes.IDENTIFY | 123  # type: ignore[operator]


# --- Code exchange and token revoke ----------------------------------------------------------------------------------

GRANT = {
    "access_token": "secret-access",
    "token_type": "Bearer",
    "expires_in": 604800,
    "scope": "identify",
    "refresh_token": "secret-refresh",
}


async def test_the_code_exchange_posts_the_grant_and_returns_the_access_token() -> None:
    client = RecordingClient()
    client.reply("POST", "/oauth2/token", GRANT)

    granted = await exchange_code(client, "the-code", URL("https://dash.example/callback"))

    assert isinstance(granted, AccessToken)
    assert granted.access_token == Token("secret-access")
    [sent] = client.requests_to("POST", "/oauth2/token")
    assert sent.data == {
        "grant_type": "authorization_code",
        "code": "the-code",
        "redirect_uri": "https://dash.example/callback",
    }


async def test_a_refused_code_exchange_returns_the_error() -> None:
    client = RecordingClient()
    client.reply("POST", "/oauth2/token", {"error": "invalid_grant", "error_description": "Invalid code"}, status=400)

    refused = await exchange_code(client, "stale-code", URL("https://dash.example/callback"))

    assert isinstance(refused, ApiResponseError)
    assert refused.status == 400


async def test_an_unreadable_token_response_returns_an_error() -> None:
    client = RecordingClient()
    client.reply("POST", "/oauth2/token", {"token_type": "Bearer"})

    assert isinstance(await exchange_code(client, "the-code", URL("https://dash.example/callback")), ApiResponseError)


async def test_revoking_posts_the_access_token() -> None:
    client = RecordingClient()
    client.reply("POST", "/oauth2/token/revoke", {})

    assert await revoke_token(client, Token("secret-access")) is None
    [sent] = client.requests_to("POST", "/oauth2/token/revoke")
    assert sent.data == {"token": "secret-access", "token_type_hint": "access_token"}


async def test_a_refused_revoke_returns_the_error() -> None:
    client = RecordingClient()
    client.fail("POST", "/oauth2/token/revoke", ApiResponseError(code=0, message="401: Unauthorized", status=401))

    assert isinstance(await revoke_token(client, Token("secret-access")), ApiResponseError)
