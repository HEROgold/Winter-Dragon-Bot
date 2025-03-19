"""Module that contains our Modal."""
import discord

from bot.core.log import LoggerMixin


class Modal(discord.ui.Modal, LoggerMixin):
    """Subclass the discord.ui.Modal and include a loggers."""
