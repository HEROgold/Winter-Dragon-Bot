"""Unit tests: NUMBER options, and Lookup autocomplete on commands and subcommands (no network)."""

from typing import TYPE_CHECKING, Annotated, ClassVar

import pytest
from sqlmodel import Session, select
from wd_bot.bot import Bot
from wd_bot.cogs import Cog, GroupCog
from wd_bot.commands import Command, CommandDefinition, Describe, Lookup
from wd_bot.testing import cog_command, detached_cog
from wd_db.extension.lifecycle import soft_delete
from wd_discord import AutocompleteInteraction
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import InteractionData, InteractionDataOption, InteractionType
from wd_discord.interactions import (
    ApplicationCommandOptionChoice,
    ApplicationCommandOptionType,
)
from wd_discord.limits import ELLIPSIS, MAX_CHOICE_NAME_LENGTH, MAX_CHOICES

from winter_dragon.cogs.tournament.models import TeamMode, Tournament, TournamentMatch


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine
    from wd_discord import CommandInteraction
    from wd_discord.testing import RecordingClient


CALLBACK = "/interactions/1/tok/callback"


class _Pets(Cog, auto_load=False):
    received: ClassVar[list[object]] = []

    async def pet_names(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        names = ["cat", "dog", "cow"]
        return [ApplicationCommandOptionChoice(name=name, value=name) for name in names if current in name]

    @Cog.command(name="pet", description="Pick a pet")
    async def pet(self, interaction: CommandInteraction, name: Annotated[str, Lookup(pet_names)], weight: float = 1.0) -> None:
        _Pets.received.append(weight)


class _Many(GroupCog, name="many", auto_load=False):
    """Many choices."""

    async def choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        return [ApplicationCommandOptionChoice(name=f"{current}{index}", value=str(index)) for index in range(40)]

    @Cog.command(name="pick", description="Pick one")
    async def pick(self, interaction: CommandInteraction, choice: Annotated[str, Lookup(choices)]) -> None:
        return None


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
    return detached_cog(cls)


def test_float_parameter_is_a_number_option() -> None:
    options = {option.name: option for option in _Pets.pet.options()}
    assert options["weight"].type == ApplicationCommandOptionType.NUMBER
    assert not options["weight"].required


def test_autocompleted_option_is_flagged() -> None:
    options = {option.name: option for option in _Pets.pet.options()}
    assert options["name"].autocomplete is True
    assert options["weight"].autocomplete is None


def test_lookup_is_part_of_the_signature() -> None:
    assert "Lookup(pet_names)" in _Pets.pet.signature()


async def test_a_plain_lookup_option_gets_the_submitted_value(make_interaction: InteractionFactory) -> None:
    received: list[object] = []

    async def handler(self: object, interaction: CommandInteraction, name: Annotated[str, Lookup(_no_rows)]) -> None:  # noqa: ARG001
        received.append(name)

    options = [InteractionDataOption(name="name", type=3, value="cat")]
    assert await cog_command(handler, CommandDefinition("pet", "d")).invoke(object(), make_interaction("pet", options=options))
    assert received == ["cat"]


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


class _Cups(Cog, auto_load=False):
    received: ClassVar[list[object]] = []

    @Cog.command(name="cup", description="Show a cup")
    async def cup(
        self,
        interaction: CommandInteraction,
        cup: Annotated[Tournament, Lookup(cup_choices), Describe("The cup to show")],
    ) -> None:
        _Cups.received.append(cup)

    async def cup_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        with Session(self.bind) as session:
            cups = session.exec(select(Tournament)).all()
        return [Lookup.choice(cup, cup.name) for cup in cups if current in cup.name]


async def _no_rows(self: object, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:  # noqa: ARG001
    return []


def _cup(session: Session, name: str = "Cup") -> Tournament:
    cup = Tournament(guild_id=1, channel_id=20, organiser_id=3, name=name, mode=TeamMode.SOLO, team_size=1)
    session.add(cup)
    session.commit()
    session.refresh(cup)
    return cup


def _cups(engine: Engine, discord_client: RecordingClient) -> _Cups:
    return detached_cog(_Cups, engine=engine, client=discord_client)


def test_a_lookup_option_is_a_string_with_autocomplete() -> None:
    (option,) = _Cups.cup.options()
    assert (option.type, option.autocomplete, option.description) == (
        ApplicationCommandOptionType.STRING,
        True,
        "The cup to show",
    )


def test_a_lookup_choice_names_the_table_and_the_id_and_cuts_long_names(engine: Engine) -> None:
    with Session(engine) as session:
        cup = _cup(session, "x" * 150)
        choice = Lookup.choice(cup, cup.name)
    assert choice.value == f"tournament:{cup.id}"
    assert choice.name == "x" * (MAX_CHOICE_NAME_LENGTH - 1) + ELLIPSIS


async def test_a_lookup_option_suggests_from_the_named_method(engine: Engine, discord_client: RecordingClient) -> None:
    with Session(engine) as session:
        first_id = _cup(session, "Spring").id
        _cup(session, "Autumn")
    options = [InteractionDataOption(name="cup", type=3, value="Spr", focused=True)]
    assert await _Cups.cup.complete(_cups(engine, discord_client), _autocomplete(discord_client, "cup", options))
    assert discord_client.requests_to("POST", CALLBACK)[0].json["data"]["choices"] == [
        {"name": "Spring", "value": f"tournament:{first_id}"},
    ]


async def test_a_lookup_value_gives_the_handler_the_row(
    engine: Engine,
    discord_client: RecordingClient,
    make_interaction: InteractionFactory,
) -> None:
    _Cups.received = []
    with Session(engine) as session:
        cup = _cup(session)
    options = [InteractionDataOption(name="cup", type=3, value=f"tournament:{cup.id}")]
    assert await _Cups.cup.invoke(_cups(engine, discord_client), make_interaction("cup", options=options))
    (received,) = _Cups.received
    assert isinstance(received, Tournament)
    assert (received.id, received.name) == (cup.id, "Cup")


@pytest.mark.parametrize("value", ["whatever I typed", "tournament:abc", "tournamentmatch:1", "tournament:999"])
async def test_a_lookup_value_that_names_no_row_is_refused(
    engine: Engine,
    discord_client: RecordingClient,
    make_interaction: InteractionFactory,
    value: str,
) -> None:
    _Cups.received = []
    with Session(engine) as session:
        _cup(session)
    options = [InteractionDataOption(name="cup", type=3, value=value)]
    assert await _Cups.cup.invoke(_cups(engine, discord_client), make_interaction("cup", options=options))
    assert _Cups.received == []
    assert discord_client.interaction_responses()[-1]["data"]["content"] == "I can't find that cup; pick one from the list."


async def test_a_soft_deleted_row_is_refused(
    engine: Engine,
    discord_client: RecordingClient,
    make_interaction: InteractionFactory,
) -> None:
    _Cups.received = []
    with Session(engine) as session:
        cup = _cup(session)
        cup_id = cup.id
        soft_delete(session, cup)
        session.commit()
    options = [InteractionDataOption(name="cup", type=3, value=f"tournament:{cup_id}")]
    assert await _Cups.cup.invoke(_cups(engine, discord_client), make_interaction("cup", options=options))
    assert _Cups.received == []
    assert "pick one from the list" in discord_client.interaction_responses()[-1]["data"]["content"]


async def test_a_union_of_tables_loads_whichever_the_value_names(
    engine: Engine,
    discord_client: RecordingClient,
    make_interaction: InteractionFactory,
) -> None:
    received: list[object] = []

    async def handler(
        self: object,
        interaction: CommandInteraction,  # noqa: ARG001
        row: Annotated[Tournament | TournamentMatch, Lookup(_no_rows)],
    ) -> None:
        received.append(row)

    with Session(engine) as session:
        cup = _cup(session)
    options = [InteractionDataOption(name="row", type=3, value=f"tournament:{cup.id}")]
    assert await cog_command(handler, CommandDefinition("row", "d")).invoke(
        _cups(engine, discord_client),
        make_interaction("row", options=options),
    )
    assert [type(row) for row in received] == [Tournament]


def test_lookup_on_a_type_that_cannot_autocomplete_raises() -> None:
    async def handler(self: object, interaction: CommandInteraction, row: Annotated[bool, Lookup(_no_rows)]) -> None:
        """Handle."""

    with pytest.raises(TypeError, match="Lookup"):
        cog_command(handler, CommandDefinition("row", "d"))


def test_a_model_without_lookup_raises() -> None:
    async def handler(self: object, interaction: CommandInteraction, row: Tournament) -> None:
        """Handle."""

    with pytest.raises(TypeError, match="Lookup"):
        cog_command(handler, CommandDefinition("row", "d"))


def test_a_lookup_naming_a_missing_cog_method_raises() -> None:
    with pytest.raises(TypeError, match="nowhere"):

        class _Broken(Cog, auto_load=False):
            @Cog.command(name="row", description="d")
            async def row(
                self,
                interaction: CommandInteraction,
                row: Annotated[Tournament, Lookup(nowhere)],  # noqa: F821,
            ) -> None:
                """Handle."""


def test_a_command_outside_a_cog_has_no_options() -> None:
    async def handler(self: object, interaction: CommandInteraction, count: int) -> None:
        """Handle."""

    with pytest.raises(TypeError, match="isn't defined on a Cog"):
        list(Command(handler, CommandDefinition("row", "d")).options())
