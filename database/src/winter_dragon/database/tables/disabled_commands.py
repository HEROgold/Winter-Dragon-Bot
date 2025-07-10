from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.channel import Channels
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.guild import Guilds
from winter_dragon.database.tables.user import Users


class DisabledCommands(SQLModel, table=True):

    command_id: int = Field(foreign_key=get_foreign_key(Commands, "id"), primary_key=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users, "id"), nullable=True)
    channel_id: int = Field(foreign_key=get_foreign_key(Channels, "id"), nullable=True)
    guild_id: int = Field(foreign_key=get_foreign_key(Guilds, "id"), nullable=True)

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
