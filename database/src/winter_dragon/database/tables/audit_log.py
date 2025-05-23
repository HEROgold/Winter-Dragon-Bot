from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel


if TYPE_CHECKING:
    from discord import AuditLogEntry


class AuditLog(SQLModel, table=True):

    id: int = Field(default=None, sa_column=Column(BigInteger(), primary_key=True))
    action: int # AuditLogAction
    reason: str | None = Field(default=None, nullable=True)
    created_at: datetime
    target_id: str
    category: int # AuditLogActionCategory

    @classmethod
    def from_audit_log(cls, entry: "AuditLogEntry") -> Self:
        """Create an AuditLog instance from a Discord AuditLogEntry."""
        from winter_dragon.database import session

        if entry.target is None:
            msg = f"Target should be AuditLogEntry.target type, but is {type(entry.target)}"
            raise ValueError(msg)
        if entry.category is None:
            msg = f"Category should be AuditLogEntry.category type, but is {type(entry.category)}"
            raise ValueError(msg)
        with session:
            audit = cls(
                id=entry.id,
                action=entry.action.value,
                reason=entry.reason,
                created_at=entry.created_at,
                target_id=str(entry.target.id),
                category=entry.category.value,
            )
            session.add(audit)
            session.commit()
        return audit
