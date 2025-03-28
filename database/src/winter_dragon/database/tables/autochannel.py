# if TYPE_CHECKING:
from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import CHANNELS_ID


class AutoChannel(SQLModel, table=True):

    id: int
    channel_id: int = Field(foreign_key=CHANNELS_ID)
