
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables import Base
from database.tables.definitions import CHANNELS_ID, USERS_ID


if TYPE_CHECKING:
    from database.tables.channels import Channel
    from database.tables.users import User
else:
    Channel = "channels"
    User = "users"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    content: Mapped[str] = mapped_column(String(2000))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID), nullable=True)

    user: Mapped["User"] = relationship(back_populates="messages", foreign_keys=[user_id])
    channel: Mapped["Channel"] = relationship(back_populates="messages", foreign_keys=[channel_id])
