"""UI primitives built on top of discord.py's button component."""

from typing import TypedDict

from discord import ButtonStyle, Emoji, PartialEmoji
from discord.ui import Button as DiscordButton
from herogold.log import LoggerMixin


class ButtonProperties(TypedDict):
    """Properties for a Discord button."""

    style: ButtonStyle
    label: str | None
    disabled: bool
    custom_id: str | None
    url: str | None
    emoji: str | Emoji | PartialEmoji | None
    row: int | None
    sku_id: int | None
    id_: int | None


class Button(DiscordButton, LoggerMixin):
    """Discord button with logging and consistent defaults."""

    def __init__(
        self,
        *,
        properties: ButtonProperties,
    ) -> None:
        """Initialize the button with various parameters."""
        super().__init__(
            style=properties.style,
            label=properties.label,
            disabled=properties.disabled,
            custom_id=properties.custom_id,
            url=properties.url,
            emoji=properties.emoji,
            row=properties.row,
            sku_id=properties.sku_id,
            id=properties.id_,
        )
