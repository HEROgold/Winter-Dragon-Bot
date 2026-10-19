"""Unit tests: template routes render encoded paths and collapse to Discord's major-param rate-limit keys."""

from __future__ import annotations

lazy import pytest
lazy from wd_discord.route import Route


CHANNEL_ID = 111
GUILD_ID = 222
MESSAGE_ID = 333
APPLICATION_ID = 444
TOKEN = "aW50ZXJhY3Rpb24-token_x"


def test_path_interleaves_parameters() -> None:
    assert Route(t"/channels/{CHANNEL_ID}/messages/{MESSAGE_ID}").path == "/channels/111/messages/333"


def test_path_keeps_literal_segments() -> None:
    assert Route(t"/users/@me/guilds/{GUILD_ID}").path == "/users/@me/guilds/222"


def test_path_encodes_parameters_as_one_segment() -> None:
    emoji = "a/b?c=d"
    assert Route(t"/channels/{CHANNEL_ID}/reactions/{emoji}").path == "/channels/111/reactions/a%2Fb%3Fc%3Dd"


def test_path_applies_format_spec() -> None:
    assert Route(t"/n/{7:03d}").path == "/n/007"


def test_concatenated_templates_render_as_one_path() -> None:
    route = Route(t"/webhooks/{APPLICATION_ID}/{TOKEN}" + t"/messages/@original")
    assert route.path == f"/webhooks/444/{TOKEN}/messages/@original"


@pytest.mark.parametrize(
    ("route", "expected"),
    [
        (Route(t"/channels/{CHANNEL_ID}/messages/{MESSAGE_ID}"), "PATCH channels/111/messages/{id}"),
        (Route(t"/guilds/{GUILD_ID}/channels"), "PATCH guilds/222/channels"),
        (Route(t"/users/@me/guilds/{GUILD_ID}"), "PATCH users/@me/guilds/222"),
        (Route(t"/users/{MESSAGE_ID}"), "PATCH users/{id}"),
        (Route(t"/applications/@me"), "PATCH applications/@me"),
        (Route(t"/webhooks/{APPLICATION_ID}/{TOKEN}/messages/@original"), "PATCH webhooks/444/{id}/messages/@original"),
        (Route(t"/interactions/{MESSAGE_ID}/{TOKEN}/callback"), "PATCH interactions/{id}/{id}/callback"),
    ],
)
def test_key_keeps_only_major_parameters(route: Route, expected: str) -> None:
    assert route.key("PATCH") == expected


def test_key_ignores_prefix_that_only_ends_like_a_major_one() -> None:
    assert Route(t"/myguilds/{GUILD_ID}").key("GET") == "GET myguilds/{id}"


def test_key_collapses_interaction_tokens_to_one_key() -> None:
    first = Route(t"/interactions/{1}/{'token-a'}/callback").key("POST")
    second = Route(t"/interactions/{2}/{'token-b'}/callback").key("POST")
    assert first == second
