"""Track currently synced definition signatures.

When the signature of any command changes, sync the command to Discord, and update the stored signature for that command.
"""

from __future__ import annotations

lazy from herogold.log import LoggerMixin
lazy from sqlmodel import Field
lazy from wd_db.extension.model import SQLModel


class SyncedCommand(SQLModel, table=True):
    """Table to track the signatures of commands that have been synced with Discord."""

    command_name: str = Field(unique=True)
    signature: str


class AutoSync(LoggerMixin):
    """Utility class to manage automatic syncing of command signatures."""
