from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlmodel import Field, SQLModel


if TYPE_CHECKING:
    from discord import AuditLogEntry


class AuditLog(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    action: int # AuditLogAction
    reason: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(nullable=True)
    target_id: int = Field(nullable=True)
    category: int = Field(nullable=True) # AuditLogActionCategory

    @classmethod
    def from_audit_log(cls, entry: "AuditLogEntry") -> Self:
    # TODO: This METHOD needs some work to work with SQLModel
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
                target_id=int(entry.target.id),
                category=entry.category.value,
            )
            session.add(audit)
            session.commit()
        return audit
