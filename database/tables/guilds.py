from datetime import datetime
from typing import Self

from discord import AuditLogAction, AuditLogActionCategory, AuditLogEntry
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables import Base, session
from database.tables.channels import Channel
from database.tables.guilds import Guild


class SyncBanGuild(Base):
    __tablename__ = "sync_ban_guilds"

    guild_id: Mapped[int] = mapped_column(ForeignKey(Guild.id), primary_key=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, autoincrement=True)
    action: Mapped[AuditLogAction] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=True)
    category: Mapped[AuditLogActionCategory] = mapped_column(Integer, nullable=True)
    # # changes: Mapped[AuditLogChanges] = mapped_column(, nullable=True)
    # before: Mapped[AuditLogDiff] = mapped_column(String, nullable=True)
    # after: Mapped[AuditLogDiff] = mapped_column(String, nullable=True)

    @classmethod
    def from_audit_log(cls, entry: AuditLogEntry) -> Self:
        with session:
            audit = cls(
                id = entry.id,
                action = entry.action,
                reason = entry.reason,
                created_at = entry.created_at,
                target = entry.target,
                category = entry.category,
                # changes = entry.changes,
                # before = entry.before,
                # after = entry.after,
            )
            session.add(audit)
            session.commit()
        return audit


class Welcome(Base):
    __tablename__ = "welcome"

    guild_id: Mapped[int] = mapped_column(ForeignKey(Guild.id), primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey(Channel.id))
    message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean)


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    channels: Mapped[list["Channel"]] = relationship(back_populates="guild")
