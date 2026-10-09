"""Unit tests: NUMBER options, and autocomplete handlers on commands and subcommands (no network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, ClassVar

import pytest
from wd_bot.bot import Bot
from wd_bot.cogs import Cog, GroupCog
from wd_discord import AutocompleteInteraction
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import InteractionData, InteractionDataOption, InteractionType
from wd_discord.interactions import MAX_CHOICES, ApplicationCommandOptionChoice, ApplicationCommandOptionType


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from wd_discord import CommandInteraction
    from wd_discord.testing import RecordingClient


CALLBACK = "/interactions/1/tok/callback"


class _Pets(Cog, auto_load=False):
    received: ClassVar[list[object]] = []

    @Cog.command(name="pet", description="Pick a pet")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def pet(self, interaction: CommandInteraction, name: str, weight: float = 1.0) -> None:
        _Pets.received.append(weight)

    @pet.autocomplete("name")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def pet_names(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        names = ["cat", "dog", "cow"]
        return [ApplicationCommandOptionChoice(name=name, value=name) for name in names if current in name]


class _Many(GroupCog, name="many", auto_load=False):
    """Many choices."""

    @Cog.command(name="pick", description="Pick one")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def pick(self, interaction: CommandInteraction, choice: str) -> None:
        return None

    @pick.autocomplete("choice")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        return [ApplicationCommandOptionChoice(name=f"{current}{index}", value=str(index)) for index in range(40)]


def _autocomplete(client: RecordingClient, name: str, options: list[InteractionDataOption]) -> AutocompleteInteraction:
    model = AutocompleteInteractionModel(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE,
        token="tok",  # noqa: S106
        version=1,
        data=InteractionData(id="10", name=name, type=1, options=options),
    )
    return AutocompleteInteraction(client, model)


def _cog[C: Cog](cls: type[C]) -> C:
    cog = cls.__new__(cls)
    cog.bot = SimpleNamespace()  # pyright: ignore[reportAttributeAccessIssue]
    return cog


def test_float_parameter_is_a_number_option() -> None:
    options = {option.name: option for option in _Pets.pet.options()}
    assert options["weight"].type == ApplicationCommandOptionType.NUMBER
    assert not options["weight"].required


def test_autocompleted_option_is_flagged() -> None:
    options = {option.name: option for option in _Pets.pet.options()}
    assert options["name"].autocomplete is True
    assert options["weight"].autocomplete is None


def test_autocomplete_is_part_of_the_signature() -> None:
    assert "autocomplete: ['name']" in _Pets.pet.signature()


def test_autocomplete_on_an_unknown_option_raises() -> None:
    with pytest.raises(TypeError, match="can't autocomplete"):
        _Pets.pet.autocomplete("missing")


async def test_whole_number_reaches_a_float_parameter_as_float(make_interaction: InteractionFactory) -> None:
    _Pets.received = []
    options = [
        InteractionDataOption(name="name", type=3, value="cat"),
        InteractionDataOption(name="weight", type=10, value=4),
    ]
    assert await _Pets.pet.invoke(_cog(_Pets), make_interaction("pet", options=options))
    assert _Pets.received == [4.0]
    assert isinstance(_Pets.received[0], float)


async def test_decimal_number_option_parses(make_interaction: InteractionFactory) -> None:
    _Pets.received = []
    options = [
        InteractionDataOption(name="name", type=3, value="cat"),
        InteractionDataOption(name="weight", type=10, value=4.5),
    ]
    assert await _Pets.pet.invoke(_cog(_Pets), make_interaction("pet", options=options))
    assert _Pets.received == [4.5]


async def test_complete_suggests_for_the_focused_option(discord_client: RecordingClient) -> None:
    options = [InteractionDataOption(name="name", type=3, value="c", focused=True)]
    assert await _Pets.pet.complete(_cog(_Pets), _autocomplete(discord_client, "pet", options))
    assert discord_client.requests_to("POST", CALLBACK)[0].json == {
        "type": 8,
        "data": {"choices": [{"name": "cat", "value": "cat"}, {"name": "cow", "value": "cow"}]},
    }


async def test_complete_without_a_handler_for_the_focused_option_fails(discord_client: RecordingClient) -> None:
    options = [InteractionDataOption(name="weight", type=10, value=1, focused=True)]
    assert not await _Pets.pet.complete(_cog(_Pets), _autocomplete(discord_client, "pet", options))
    assert discord_client.sent == []


async def test_group_routes_autocomplete_to_its_subcommand_and_caps_choices(discord_client: RecordingClient) -> None:
    (group,) = _Many.app_commands()
    sub = InteractionDataOption(
        name="pick",
        type=1,
        options=[InteractionDataOption(name="choice", type=3, value="x", focused=True)],
    )
    assert await group.complete(_cog(_Many), _autocomplete(discord_client, "many", [sub]))
    choices = discord_client.requests_to("POST", CALLBACK)[0].json["data"]["choices"]
    assert len(choices) == MAX_CHOICES
    assert choices[0] == {"name": "x0", "value": "0"}


async def test_bot_dispatches_autocomplete_to_the_command(discord_client: RecordingClient) -> None:
    bot = Bot()
    cog = _cog(_Pets)
    bot.registry.register(cog)  # registering without add_cog's side effects
    options = [InteractionDataOption(name="name", type=3, value="d", focused=True)]
    await bot._dispatch_interaction(_autocomplete(discord_client, "pet", options))  # noqa: SLF001
    assert discord_client.interaction_responses() == [{"type": 8, "data": {"choices": [{"name": "dog", "value": "dog"}]}}]
