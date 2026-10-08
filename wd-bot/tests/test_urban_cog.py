"""Unit tests: Urban Dictionary lookups, their embeds, and the /urban commands (no network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import httpxyz
import pytest
from wd_config.urban import UrbanSettings
from wd_discord.embed import MAX_EMBED_CHARACTERS
from wd_discord.gateway.events import InteractionDataOption

from winter_dragon.cogs.urban import Definition, LookupFailed, Urban, UrbanDictionary, build_embed


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from wd_discord.testing import RecordingClient


FOLLOWUP = "/webhooks/2/tok"


def _definition(index: int, text: str = "a meaning") -> dict[str, object]:
    return {
        "word": f"word{index}",
        "definition": text,
        "permalink": f"https://urbanup.com/{index}",
        "thumbs_up": 10,
        "thumbs_down": 2,
        "author": "someone",
    }


def _http(handler: httpxyz.Response | Exception) -> httpxyz.AsyncClient:
    def respond(request: httpxyz.Request) -> httpxyz.Response:
        if isinstance(handler, Exception):
            raise handler
        return handler

    return httpxyz.AsyncClient(transport=httpxyz.MockTransport(respond))


def _cog(http: httpxyz.AsyncClient) -> Urban:
    cog = Urban.__new__(Urban)
    cog.bot = SimpleNamespace()  # pyright: ignore[reportAttributeAccessIssue]
    cog.http = http
    return cog


async def test_define_parses_definitions() -> None:
    http = _http(httpxyz.Response(200, json={"list": [_definition(1), _definition(2)]}))
    async with UrbanDictionary(http) as urban:
        definitions = await urban.define("yeet")
    assert isinstance(definitions, list)
    assert [definition.word for definition in definitions] == ["word1", "word2"]


@pytest.mark.parametrize(
    "answer",
    [
        httpxyz.Response(503),
        httpxyz.Response(200, json={"unexpected": True}),
        httpxyz.ConnectError("down"),
    ],
)
async def test_failed_lookup_is_a_value(answer: httpxyz.Response | Exception) -> None:
    async with UrbanDictionary(_http(answer)) as urban:
        assert isinstance(await urban.random(), LookupFailed)


def test_embed_truncates_long_definitions_to_the_field_limit() -> None:
    definition = Definition.model_validate(_definition(1, "x" * 5000))
    (field,) = build_embed("t", [definition], limit=5).fields or []
    assert len(field.value) == 1024
    assert field.value.endswith("https://urbanup.com/1")


def test_embed_stays_within_discords_limits() -> None:
    definitions = [Definition.model_validate(_definition(index, "x" * 5000)) for index in range(30)]
    embed = build_embed("t", definitions, limit=30)
    assert embed.character_count() <= MAX_EMBED_CHARACTERS
    assert 0 < len(embed.fields or []) <= 25


def test_embed_shows_at_most_the_limit() -> None:
    definitions = [Definition.model_validate(_definition(index)) for index in range(10)]
    assert len(build_embed("t", definitions, limit=3).fields or []) == 3


async def test_search_replies_with_an_embed(make_interaction: InteractionFactory, discord_client: RecordingClient) -> None:
    cog = _cog(_http(httpxyz.Response(200, json={"list": [_definition(1)]})))
    options = [InteractionDataOption(name="query", type=3, value="yeet")]

    await Urban.search.invoke(cog, make_interaction("urban"), options)

    (followup,) = discord_client.requests_to("POST", FOLLOWUP)
    (embed,) = followup.json["embeds"]
    assert embed["title"] == "Urban Dictionary: yeet"
    assert embed["fields"][0]["name"] == "1. word1"


async def test_search_without_results_says_so(make_interaction: InteractionFactory, discord_client: RecordingClient) -> None:
    cog = _cog(_http(httpxyz.Response(200, json={"list": []})))
    options = [InteractionDataOption(name="query", type=3, value="qwzx")]

    await Urban.search.invoke(cog, make_interaction("urban"), options)

    (followup,) = discord_client.requests_to("POST", FOLLOWUP)
    assert followup.json["content"] == "No definitions found for `qwzx`."


async def test_random_can_be_turned_off(
    monkeypatch: pytest.MonkeyPatch,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    monkeypatch.setattr(UrbanSettings, "allow_random", False)
    cog = _cog(_http(httpxyz.Response(200, json={"list": [_definition(1)]})))

    await Urban.random.invoke(cog, make_interaction("urban"), [])

    assert discord_client.interaction_responses() == [
        {"type": 4, "data": {"content": "Random definitions are turned off.", "flags": 64}},
    ]
