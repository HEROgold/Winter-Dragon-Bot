from discord import ButtonStyle, Emoji, PartialEmoji
from discord.ui import Button as DiscordButton

from winter_dragon.logging import LoggerMixin


class Button(DiscordButton, LoggerMixin):
    def __init__(
        self,
        *,
        style: ButtonStyle = ButtonStyle.secondary,
        label: str | None = None,
        disabled: bool = False,
        custom_id: str | None = None,
        url: str | None = None,
        emoji: str | Emoji | PartialEmoji | None = None,
        row: int | None = None,
        sku_id: int | None = None,
        id_: int | None = None,
    ):
        """Initialize the button with various parameters."""
        super().__init__(
            style=style,
            label=label,
            disabled=disabled,
            custom_id=custom_id,
            url=url,
            emoji=emoji,
            row=row,
            sku_id=sku_id,
            id=id_,
        )
