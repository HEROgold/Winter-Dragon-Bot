"""Package that contains extensions for WinterDragon bot."""
from __future__ import annotations

from .bot_activity import BotActivity
from .bot_control import BotControl
from .bot_metrics import BotMetrics
from .command_manager import CommandManager
from .database_manager import CogEvents
from .prometheus import Prometheus
from .sync import Sync


__all__ = [
    "BotActivity",
    "BotControl",
    "BotMetrics",
    "CogEvents ",
    "CommandManager",
    "Prometheus",
    "Sync",
]
