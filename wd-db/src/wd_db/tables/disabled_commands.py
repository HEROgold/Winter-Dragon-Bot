from __future__ import annotations

from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.channel import Channels
from wd_db.tables.command import Commands
from wd_db.tables.guild import Guilds
from wd_db.tables.user import Users


class DisabledCommands(SQLModel, table=True):
    command_id: int = Field(foreign_key=get_foreign_key(Commands), unique=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users), nullable=True)
    channel_id: int = Field(foreign_key=get_foreign_key(Channels), nullable=True)
    guild_id: int = Field(foreign_key=get_foreign_key(Guilds), nullable=True)
    reason: str = Field(default="No reason provided")

    def __init__(self, **kw: int) -> None:
        id_limit = 2

        if len(kw) > id_limit:
            msg = f"Only 2 arguments expected, got {len(kw)}!"
            raise ValueError(msg)

        command_id = kw.get("command_id")

        if not command_id:
            raise ValueError("command_id is required!")  # noqa: EM101, TRY003

        user_id = kw.get("_user_id")
        channel_id = kw.get("_channel_id")
        guild_id = kw.get("_guild_id")

        if not any([user_id, channel_id, guild_id]):
            raise ValueError("At least one of user_id, channel_id, or guild_id is required!")  # noqa: EM101, TRY003
        if sum([bool(user_id), bool(channel_id), bool(guild_id)]) > 1:
            raise ValueError("Only one of user_id, channel_id, or guild_id can be set!")  # noqa: EM101, TRY003
        super().__init__(**kw)

    @property
    def target_id(self) -> int:
        """Return the target ID. Could be a user, channel, or guild ID."""
        return self.user_id or self.channel_id or self.guild_id
