"""Unit tests: what the bot names each traced interaction (no network)."""

from typing import TYPE_CHECKING

from wd_bot.tracing import interaction_name
from wd_discord import AutocompleteInteraction
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import InteractionData, InteractionDataOption, InteractionType
from wd_discord.interactions import ApplicationCommandOptionType


if TYPE_CHECKING:
    from conftest import ComponentInteractionFactory, InteractionFactory, ModalSubmitFactory
    from wd_discord.testing import RecordingClient


SUB = ApplicationCommandOptionType.SUB_COMMAND
GROUP = ApplicationCommandOptionType.SUB_COMMAND_GROUP
STRING = ApplicationCommandOptionType.STRING


def test_a_command_is_named_by_its_path_without_option_values(make_interaction: InteractionFactory) -> None:
    value = InteractionDataOption(name="who", type=STRING, value="someone private")
    options = [
        InteractionDataOption(
            name="admin", type=GROUP, options=[InteractionDataOption(name="reset", type=SUB, options=[value])]
        )
    ]

    assert interaction_name(make_interaction("stats", options=options)) == "/stats admin reset"
    assert interaction_name(make_interaction("ping")) == "/ping"


def test_an_autocomplete_is_named_after_its_command(discord_client: RecordingClient) -> None:
    typed = InteractionDataOption(name="name", type=STRING, value="ca", focused=True)
    model = AutocompleteInteractionModel(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE,
        token="tok",  # noqa: S106
        version=1,
        data=InteractionData(id="10", name="pet", type=1, options=[typed]),
    )

    assert interaction_name(AutocompleteInteraction(discord_client, model)) == "/pet (autocomplete)"


def test_components_and_modals_are_named_by_their_custom_id_prefix(
    make_component_interaction: ComponentInteractionFactory,
    make_modal_submit: ModalSubmitFactory,
) -> None:
    assert interaction_name(make_component_interaction("tourney-leave:42")) == "component tourney-leave"
    assert interaction_name(make_modal_submit("tourney:7", {"name": "x"})) == "modal tourney"
