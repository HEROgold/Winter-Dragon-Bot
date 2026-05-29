from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, select

from wd_db.extension.model import SQLModel


if TYPE_CHECKING:
    from sqlalchemy.sql.selectable import Exists


class Commands(SQLModel, table=True):
    """Commands table to store information about bot commands."""

    qual_name: str = Field()
    call_count: int = Field()

    def disabled(self) -> Exists:
        """Return a DisabledCommands instance for this command."""
        from wd_db.tables.disabled_commands import DisabledCommands  # noqa: PLC0415
        return select(DisabledCommands).where(DisabledCommands.command_id == self.id).exists()
