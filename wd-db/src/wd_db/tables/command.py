from sqlmodel import Field, select

from wd_db.extension.model import SQLModel


class Commands(SQLModel, table=True):
    """Commands table to store information about bot commands."""

    qual_name: str = Field()
    call_count: int = Field()

    def disabled(self):
        """Return a DisabledCommands instance for this command."""
        from wd_db.tables.disabled_commands import DisabledCommands  # noqa: PLC0415
        return select(DisabledCommands).where(DisabledCommands.command_id == self.id).exists()
