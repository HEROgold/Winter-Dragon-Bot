"""What the bot names each traced interaction: the command path it ran, or the custom ID prefix it hit.

The names group transactions in Sentry, so they hold no user input: a subcommand path, never option values; a custom
ID's prefix, never its arguments.
"""

lazy from typing import TYPE_CHECKING

lazy from wd_discord import (
    AutocompleteInteraction,
    CommandInteraction,
    ComponentInteraction,
    ModalSubmitInteraction,
)
lazy from wd_discord.interactions import ApplicationCommandOptionType

lazy from wd_bot.components import parse_custom_id


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Sequence

    lazy from wd_discord import AnyInteraction
    lazy from wd_discord.gateway.events import InteractionDataOption


def subcommand_path(options: Sequence[InteractionDataOption]) -> Generator[str]:
    """Yield the subcommand group and subcommand ``options`` choose, outermost first."""
    nested = (ApplicationCommandOptionType.SUB_COMMAND, ApplicationCommandOptionType.SUB_COMMAND_GROUP)
    for option in options:
        if option.type in nested:
            yield option.name
            yield from subcommand_path(option.options or [])
            return


def interaction_name(interaction: AnyInteraction) -> str:
    """Return the transaction name of ``interaction``: ``/stats reset``, ``/remind (autocomplete)``, ``modal tourney``."""
    match interaction:
        case CommandInteraction():
            return " ".join([f"/{interaction.command_name}", *subcommand_path(interaction.options)])
        case AutocompleteInteraction():
            return " ".join([f"/{interaction.command_name}", *subcommand_path(interaction.options), "(autocomplete)"])
        case ComponentInteraction():
            return f"component {parse_custom_id(interaction.custom_id)[0]}"
        case ModalSubmitInteraction():
            return f"modal {parse_custom_id(interaction.custom_id)[0]}"
        case _:
            return type(interaction).__name__
