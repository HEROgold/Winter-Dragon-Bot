"""Unit tests: modal handlers and MODAL_SUBMIT dispatch."""

import asyncio
from typing import TYPE_CHECKING

from wd_bot.bot import Bot
from wd_bot.cogs import Cog
from wd_bot.components import ModalHandler


if TYPE_CHECKING:
    from conftest import ModalSubmitFactory
    from wd_discord import ModalSubmitInteraction
    from wd_discord.testing import RecordingClient


SUBMITS: list[tuple[tuple[str, ...], dict[str, str]]] = []


class _GuessCog(Cog, auto_load=False):
    @Cog.modal("guess")
    async def guess(self, interaction: ModalSubmitInteraction, *args: str) -> None:
        SUBMITS.append((args, interaction.values))


class _BrokenGuessCog(Cog, auto_load=False):
    @Cog.modal("broken")
    async def guess(self, interaction: ModalSubmitInteraction, *args: str) -> None:  # noqa: ARG002
        msg = "handler broke"
        raise RuntimeError(msg)


def _make_bot(client: RecordingClient) -> Bot:
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    bot.client = client
    return bot


def test_modal_custom_id_carries_args() -> None:
    assert _GuessCog.guess.custom_id(7) == "guess:7"
    assert [handler.prefix for handler in _GuessCog.modals()] == ["guess"]
    assert isinstance(_GuessCog.guess, ModalHandler)


async def test_dispatch_routes_a_submit_to_its_handler(
    make_modal_submit: ModalSubmitFactory,
    discord_client: RecordingClient,
) -> None:
    SUBMITS.clear()
    bot = _make_bot(discord_client)
    await bot.add_cog(_GuessCog(bot=bot))

    await bot._dispatch_interaction(make_modal_submit("guess:7", {"guess": "e"}))

    assert SUBMITS == [(("7",), {"guess": "e"})]
    assert discord_client.sent == []


async def test_dispatch_ignores_unknown_modal_prefixes(
    make_modal_submit: ModalSubmitFactory,
    discord_client: RecordingClient,
) -> None:
    bot = _make_bot(discord_client)

    await bot._dispatch_interaction(make_modal_submit("nobody:1", {}))

    assert discord_client.sent == []


async def test_dispatch_sends_ephemeral_error_when_modal_handler_raises(
    make_modal_submit: ModalSubmitFactory,
    discord_client: RecordingClient,
    error_reply: dict[str, object],
) -> None:
    bot = _make_bot(discord_client)
    await bot.add_cog(_BrokenGuessCog(bot=bot))

    await bot._dispatch_interaction(make_modal_submit("broken:1", {}))

    assert discord_client.interaction_responses() == [{"type": 4, "data": error_reply}]
