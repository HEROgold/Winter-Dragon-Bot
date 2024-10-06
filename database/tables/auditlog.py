from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


if TYPE_CHECKING:
    from discord import AuditLogEntry


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, autoincrement=True)
    action: Mapped[int] = mapped_column(Integer) # AuditLogAction
    reason: Mapped[str] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=True)
    category: Mapped[int] = mapped_column(Integer, nullable=True) # AuditLogActionCategory
    # # changes: Mapped[AuditLogChanges] = mapped_column(, nullable=True)
    # before: Mapped[AuditLogDiff] = mapped_column(String, nullable=True)
    # after: Mapped[AuditLogDiff] = mapped_column(String, nullable=True)

    @classmethod
    def from_audit_log(cls, entry: "AuditLogEntry") -> Self:
        from database import session

        with session:
            audit = cls(
                id=entry.id,
                action=entry.action,
                reason=entry.reason,
                created_at=entry.created_at,
                target=entry.target,
                category=entry.category,
                # changes = entry.changes,
                # before = entry.before,
                # after = entry.after,
            )
            session.add(audit)
            session.commit()
        return audit
