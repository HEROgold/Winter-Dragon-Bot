"""Select menu components for Discord interactions."""

from typing import TypedDict, Unpack

from discord import Interaction, SelectOption
from discord.ui import Select as DiscordSelect
from herogold.log import LoggerMixin

from winter_dragon.bot.ui.abc import InteractEvent, default_interact


class SelectArgs[T](TypedDict, total=False):
    """Arguments for creating a select menu."""

    custom_id: str | None
    placeholder: str | None
    min_values: int
    max_values: int
    options: list[SelectOption] | None
    disabled: bool
    required: bool
    row: int | None
    on_interact: InteractEvent[T]

default_args: SelectArgs = {
    "custom_id": None,
    "placeholder": None,
    "min_values": 1,
    "max_values": 1,
    "options": None,
    "disabled": False,
    "required": True,
    "row": None,
    "on_interact": default_interact,
}

class Select[T](DiscordSelect, LoggerMixin):
    """Enhanced select menu with logging and callbacks."""

    def __init__(
        self,
        **kwargs: Unpack[SelectArgs[T]],
    ) -> None:
        """Initialize the select menu."""
        args: SelectArgs[T] = {**default_args, **kwargs}
        self.on_interact = kwargs.pop("on_interact")
        super().__init__(**args)  # pyright: ignore[reportCallIssue] # pyright popped values are still present.

    async def callback(self, interaction: Interaction) -> None:
        """Handle the button click event."""
        await interaction.response.defer()
        self.disabled = True
        await self.on_interact(interaction)
        self.disabled = False
        await interaction.response.edit_message(view=self.view)
