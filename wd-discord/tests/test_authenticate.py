"""Unit tests: header builders render correct, case-sensitive Discord headers."""
from __future__ import annotations

from wd_discord import Client, Token, TokenType
from wd_discord.authenticate import (
    URL,
    ContentType,
    MetaData,
    UserAgentVersion,
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


def test_content_type_header_render() -> None:
    assert render_header(content_type(ContentType.json)) == ("Content-Type", "application/json")


def test_user_agent_render() -> None:
    header = render(user_agent(URL("https://example.com"), UserAgentVersion("1.2.3"), MetaData("meta")))
    assert header == "User-Agent: DiscordBot (https://example.com, 1.2.3) meta"


def test_client_default_headers() -> None:
    headers = Client("my.token")._default_headers()
    assert headers["Authorization"] == "Bot my.token"
    assert headers["Content-Type"] == "application/json"
    assert headers["User-Agent"].startswith("DiscordBot (")
