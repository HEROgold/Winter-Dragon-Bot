import logging

import discord
from discord.utils import MISSING

from tools.config_reader import config


class Modal(discord.ui.Modal):
    logger: logging.Logger

    def __init__(
        self,
        *,
        title: str = MISSING,
        timeout: float | None = None,
        custom_id: str = MISSING,
    ) -> None:
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
