"""Unit tests: component handlers, custom_id building, MESSAGE_COMPONENT dispatch and command mentions."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from wd_bot.bot import Bot
from wd_bot.cogs import Cog
from wd_bot.components import ComponentHandler, parse_custom_id


if TYPE_CHECKING:
    from conftest import ComponentInteractionFactory
    from wd_discord import ComponentInteraction
    from wd_discord.testing import RecordingClient


CLICKS: list[tuple[str, ...]] = []


class _PagerCog(Cog, auto_load=False):
    @Cog.component("pager")
    async def turn(self, interaction: ComponentInteraction, *args: str) -> None:  # noqa: ARG002
        CLICKS.append(args)


class _BrokenPagerCog(Cog, auto_load=False):
    @Cog.component("broken")
    async def turn(self, interaction: ComponentInteraction, *args: str) -> None:  # noqa: ARG002
        msg = "handler broke"
        raise RuntimeError(msg)


def _make_bot(client: RecordingClient) -> Bot:
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    bot.client = client
    return bot


def test_custom_id_joins_prefix_and_args() -> None:
    handler = _PagerCog.turn
    assert handler.custom_id(3, "100", 2) == "pager:3:100:2"
    assert parse_custom_id("pager:3:100:2") == ("pager", ["3", "100", "2"])


def test_custom_id_rejects_args_containing_the_separator() -> None:
    with pytest.raises(ValueError, match="must not contain"):
        _PagerCog.turn.custom_id("a:b")


def test_custom_id_rejects_ids_over_100_characters() -> None:
    with pytest.raises(ValueError, match="Discord allows 100"):
        _PagerCog.turn.custom_id("x" * 100)


def test_prefix_must_not_contain_the_separator() -> None:
    async def noop(*_args: object) -> None: ...

    with pytest.raises(ValueError, match="prefix"):
        ComponentHandler(noop, prefix="a:b")


def test_cog_lists_its_component_handlers() -> None:
    assert [handler.prefix for handler in _PagerCog.components()] == ["pager"]


async def test_dispatch_routes_a_click_to_its_handler_with_args(
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    CLICKS.clear()
    bot = _make_bot(discord_client)
    await bot.add_cog(_PagerCog(bot=bot))

    await bot._dispatch_interaction(make_component_interaction("pager:3:100:2"))

    assert CLICKS == [("3", "100", "2")]
    assert discord_client.sent == []


async def test_dispatch_ignores_unknown_prefixes(
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    bot = _make_bot(discord_client)

    await bot._dispatch_interaction(make_component_interaction("nobody:1"))

    assert discord_client.sent == []


async def test_dispatch_sends_ephemeral_error_when_component_handler_raises(
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    bot = _make_bot(discord_client)
    await bot.add_cog(_BrokenPagerCog(bot=bot))

    await bot._dispatch_interaction(make_component_interaction("broken:1"))

    assert discord_client.interaction_responses() == [
        {"type": 4, "data": {"content": "Something went wrong running this command.", "flags": 64}},
    ]
