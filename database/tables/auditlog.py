from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlmodel import Field, SQLModel


if TYPE_CHECKING:
    from discord import AuditLogEntry


class AuditLog(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    action: int # AuditLogAction
    reason: str = Field(nullable=True)
    created_at: datetime = Field(nullable=True)
    target_id: int = Field(nullable=True)
    category: int = Field(nullable=True) # AuditLogActionCategory

    @classmethod
    def from_audit_log(cls, entry: "AuditLogEntry") -> Self:
    # TODO: This METHOD needs some work to work with SQLModel
        from database import session

        with session:
            audit = cls(
                id=entry.id,
                action=entry.action,
                reason=entry.reason,
                created_at=entry.created_at,
                target_id=entry.target,
                category=entry.category,
            )
            session.add(audit)
            session.commit()
        return audit
