"""Unit tests: header builders render correct, case-sensitive Discord headers."""

lazy from wd_discord import Client, Token, TokenType
lazy from wd_discord.authenticate import (
    URL,
    ContentType,
    MetaData,
    UserAgentVersion,
    client_credentials,
    content_type,
    get_auth_header,
    render,
    render_header,
    user_agent,
)


def test_token_type_is_capitalised() -> None:
    # Discord's auth scheme is case-sensitive: "Bot", not "bot".
    assert TokenType.BOT == "Bot"


def test_auth_header_render() -> None:
    name, value = render_header(get_auth_header(TokenType.BOT, Token("my.token")))
    assert (name, value) == ("Authorization", "Bot my.token")


def test_token_repr_hides_the_secret() -> None:
    token = Token("my.secret.token")
    assert "my.secret.token" not in repr(token)
    assert str(token) == "my.secret.token"


def test_content_type_header_render() -> None:
    assert render_header(content_type(ContentType.json)) == ("Content-Type", "application/json")


def test_user_agent_render() -> None:
    header = render(user_agent(URL("https://example.com"), UserAgentVersion("1.2.3"), MetaData("meta")))
    assert header == "User-Agent: DiscordBot (https://example.com, 1.2.3) meta"


def test_client_default_headers() -> None:
    headers = Client("my.token")._default_headers()
    assert headers["Authorization"] == "Bot my.token"
    assert "Content-Type" not in headers  # set per request: JSON, or multipart for uploads
    assert headers["User-Agent"].startswith("DiscordBot (")


def test_client_credentials_render_as_basic_auth() -> None:
    # base64("2:shh"), the application ID and client secret Discord's OAuth2 token endpoints take as Basic auth.
    name, value = render_header(get_auth_header(TokenType.BASIC, client_credentials(2, Token("shh"))))
    assert (name, value) == ("Authorization", "Basic MjpzaGg=")


def test_an_access_token_renders_as_bearer_auth() -> None:
    assert render_header(get_auth_header(TokenType.BEARER, Token("access"))) == ("Authorization", "Bearer access")


def test_client_credentials_hide_the_secret() -> None:
    assert "MjpzaGg" not in repr(client_credentials(2, Token("shh")))
