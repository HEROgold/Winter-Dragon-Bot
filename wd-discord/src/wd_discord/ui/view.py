"""Custom view class that extends Discord's View and includes logging capabilities."""

from __future__ import annotations

from discord.ui import View as DiscordView
from herogold.log import LoggerMixin


class View(DiscordView, LoggerMixin):
    """Custom view class that extends Discord's View and includes logging capabilities."""
