# if TYPE_CHECKING:
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import CHANNELS_ID


class AutoChannel(Base):
    __tablename__ = "autochannels"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=False)
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID))
