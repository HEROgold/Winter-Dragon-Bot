"""Module that contains our Button."""

import discord
from winter_dragon.bot.core.log import LoggerMixin


class Button(discord.ui.Button, LoggerMixin):
    """Subclass the discord.ui.Button and include a loggers."""
