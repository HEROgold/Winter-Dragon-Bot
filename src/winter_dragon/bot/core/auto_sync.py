"""Track currently synced definition signatures.

When the signature of any command changes, sync the command to Discord, and update the stored signature for that command.
"""

from inspect import signature
from typing import TYPE_CHECKING

from herogold.log import LoggerMixin
from herogold.orm.model import BaseModel
from sqlmodel import Field


if TYPE_CHECKING:
    from collections.abc import Callable


class SyncedCommand(BaseModel, table=True):
    """Table to track the signatures of commands that have been synced with Discord."""

    command_name: str = Field(primary_key=True)
    signature: str


class AutoSync(LoggerMixin):
    """Utility class to manage automatic syncing of command signatures."""

    @staticmethod
    def get_signature[**P, R](func: Callable[P, R]) -> str:
        """Generate a string representation of the function's signature."""
        return str(signature(func))
