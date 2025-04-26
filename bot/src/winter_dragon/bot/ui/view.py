"""Module that contains our View."""

import discord
from winter_dragon.bot.core.log import LoggerMixin


class View(discord.ui.View, LoggerMixin):
    """Subclass the discord.ui.View and include a loggers."""
