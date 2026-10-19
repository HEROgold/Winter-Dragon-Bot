"""Package that contains extensions for WinterDragon bot."""
from __future__ import annotations

lazy from .bot_activity import BotActivity
lazy from .bot_control import BotControl
lazy from .bot_metrics import BotMetrics
lazy from .command_manager import CommandManager
lazy from .database_manager import CogEvents
lazy from .prometheus import Prometheus
lazy from .sync import Sync


__all__ = [
    "BotActivity",
    "BotControl",
    "BotMetrics",
    "CogEvents ",
    "CommandManager",
    "Prometheus",
    "Sync",
]
