import logging
from discord.emoji import Emoji
from discord.enums import ButtonStyle
from discord.partial_emoji import PartialEmoji
import discord.ui.button

from tools.config_reader import config


class Button(discord.ui.Button):
    logger: logging.Logger

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
    ):
        super().__init__(
            style=style,
            label=label,
            disabled=disabled,
            custom_id=custom_id,
            url=url,
            emoji=emoji,
            row=row,
        )
        self.logger = logging.getLogger(
            f"{config['Main']['bot_name']}.{self.__class__.__qualname__}"
        )
