"""Package for server cogs."""
from __future__ import annotations

lazy from .announcement import Announce
lazy from .auto_assign import AutoAssign
lazy from .purge import Purge
lazy from .stats import Stats
lazy from .sync_ban import SyncedBans
lazy from .welcome import Welcome


__all__ = [
    "Announce",
    "AutoAssign",
    "Purge",
    "Stats",
    "SyncedBans",
    "Welcome",
]
