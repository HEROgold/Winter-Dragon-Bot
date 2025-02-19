from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import CHANNELS_ID, COMMANDS_ID, GUILDS_ID, USERS_ID


class DisabledCommands(Base):
    __tablename__ = "disabled_commands"

    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID), primary_key=True)
    _user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    _channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID), nullable=True)
    _guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), nullable=True)

    def __init__(self, **kw: int) -> None:
        # TODO @HEROgold: needs testing
        # 000
        id_limit = 2

        command_id = kw.get("command_id")
        if not command_id:
            raise ValueError("command_id is required!")  # noqa: EM101, TRY003
        user_id = kw.get("_user_id")
        channel_id = kw.get("_channel_id")
        guild_id = kw.get("_guild_id")

        if not any([user_id, channel_id, guild_id]):
            raise ValueError("At least one of _user_id, _channel_id, or _guild_id is required!")  # noqa: EM101, TRY003
        if len(kw) > id_limit:
            msg = f"Only 2 arguments expected, got {len(kw)}!"
            raise ValueError(msg)
        super().__init__(**kw)

    @property
    def target_id(self) -> int:
        return self._user_id or self._channel_id or self._guild_id
