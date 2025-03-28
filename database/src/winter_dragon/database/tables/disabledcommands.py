from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import CHANNELS_ID, COMMANDS_ID, GUILDS_ID, USERS_ID


class DisabledCommands(SQLModel, table=True):

    command_id: int = Field(foreign_key=COMMANDS_ID, primary_key=True)
    _user_id: int = Field(foreign_key=USERS_ID, nullable=True)
    _channel_id: int = Field(foreign_key=CHANNELS_ID, nullable=True)
    _guild_id: int = Field(foreign_key=GUILDS_ID, nullable=True)

    def __init__(self, **kw: int) -> None:
        # TODO @HEROgold: needs testing
        # 000
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
            raise ValueError("At least one of _user_id, _channel_id, or _guild_id is required!")  # noqa: EM101, TRY003
        super().__init__(**kw)


    @property
    def target_id(self) -> int:
        """Return the target ID. Could be a user, channel, or guild ID."""
        return self._user_id or self._channel_id or self._guild_id
