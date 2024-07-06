from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables import Base
from database.tables.channels import Channel
from database.tables.users import User


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    content: Mapped[str] = mapped_column(String(2000))
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    channel_id: Mapped[int] = mapped_column(ForeignKey(Channel.id), nullable=True)

    user: Mapped["User"] = relationship(back_populates="messages", foreign_keys=[user_id])
    channel: Mapped["Channel"] = relationship(back_populates="messages", foreign_keys=[channel_id])
