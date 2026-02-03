"""UI primitives built on top of discord.py's button component."""

from typing import Unpack, override

from discord import ButtonStyle, Emoji, Interaction, PartialEmoji
from discord.ui import Button as DiscordButton
from herogold.log import LoggerMixin
from sqlalchemy.util.typing import TypedDict

from winter_dragon.bot.ui.abc import default_interact

from .abc import InteractEvent


class ButtonArgs[T](TypedDict, total=False):
    """Arguments for creating a button."""

    style: ButtonStyle
    label: str | None
    disabled: bool
    custom_id: str | None
    url: str | None
    emoji: None | str | Emoji | PartialEmoji
    row: int | None
    sku_id: int | None
    id: int | None
    on_interact: InteractEvent[T]


default_args: ButtonArgs[None] = {
    "style": ButtonStyle.secondary,
    "label": None,
    "disabled": False,
    "custom_id": None,
    "url": None,
    "emoji": None,
    "row": None,
    "sku_id": None,
    "id": None,
    "on_interact": default_interact,
}


class Button[T = None](DiscordButton, LoggerMixin):
    """Discord button with logging and consistent defaults."""

    def __init__(
        self,
        **kwargs: Unpack[ButtonArgs[T]],
    ) -> None:
        """Initialize the button with various parameters."""
        args: ButtonArgs[T] = {**default_args, **kwargs}
        self.on_interact = args.pop("on_interact")
        super().__init__(**args)  # pyright: ignore[reportCallIssue] # pyright says on_interact is still present.

    async def callback(self, interaction: Interaction) -> None:
        """Handle the button click event."""
        await interaction.response.defer()
        self.disabled = True
        await self.on_interact(interaction)
        self.disabled = False
        await interaction.response.edit_message(view=self.view)


class ToggleArgs[T](TypedDict, total=False):
    """Arguments for creating a toggle button."""

    custom_id: str | None
    url: str | None
    row: int | None
    sku_id: int | None
    id: int | None
    on_interact: InteractEvent[T]


class ToggleButton[T = None](Button[T]):
    """A button that toggles a state when clicked."""

    state = False
    emojis = ("✅", "❌")

    def __init__(
        self,
        **kwargs: Unpack[ToggleArgs[T]],
    ) -> None:
        """Initialize the button with various parameters."""
        super().__init__(style=ButtonStyle.danger, label="Off", disabled=False, emoji=self.emojis[self.state], **kwargs)

    @override
    async def callback(self, interaction: Interaction) -> None:
        self.state = not self.state
        self.style = ButtonStyle.success if self.state else ButtonStyle.danger
        self.emoji = self.emojis[self.state]
        self.label = "On" if self.state else "Off"
        await super().callback(interaction)
