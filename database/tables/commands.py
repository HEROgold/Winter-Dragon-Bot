
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables import Base
from database.tables.definitions import CHANNELS_ID, COMMAND_GROUPS_ID, COMMANDS_ID, GUILDS_ID, USERS_ID


class Command(Base):
    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    qual_name: Mapped[str] = mapped_column(String(30))
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_id: Mapped[int] = mapped_column(ForeignKey(COMMAND_GROUPS_ID), nullable=True)

    parent: Mapped["CommandGroup"] = relationship(back_populates="commands", foreign_keys=[parent_id])


class DisabledCommands(Base):
    __tablename__ = "disabled_commands"

    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID), primary_key=True)
    _user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    _channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID), nullable=True)
    _guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), nullable=True)

    def __init__(self, **kw: int) -> None:
        # TODO: needs testing
        id_limit = 2
        if len(kw) > id_limit:
            msg = f"Only 2 arguments expected, got {len(kw)}!"
            raise ValueError(msg)
        super().__init__(**kw)

    @property
    def target_id(self) -> int:
        return self._user_id or self._channel_id or self._guild_id


class CommandGroup(Base):
    __tablename__ = "command_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30))

    commands: Mapped[list["Command"]] = relationship(back_populates="parent")
