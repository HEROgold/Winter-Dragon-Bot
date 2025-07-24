from datetime import datetime
from typing import TYPE_CHECKING, Self

from sqlmodel import Field
from winter_dragon.database.extension.model import DiscordID


if TYPE_CHECKING:
    from discord import AuditLogEntry


class AuditLog(DiscordID, table=True):

    action: int # AuditLogAction
    reason: str | None = Field(default=None, nullable=True)
    created_at: datetime
    target_id: str
    category: int # AuditLogActionCategory

    @classmethod
    def from_audit_log(cls, entry: "AuditLogEntry") -> Self:
        """Create an AuditLog instance from a Discord AuditLogEntry."""
        if entry.target is None:
            msg = f"Target should be AuditLogEntry.target type, but is {type(entry.target)}"
            raise ValueError(msg)
        if entry.category is None:
            msg = f"Category should be AuditLogEntry.category type, but is {type(entry.category)}"
            raise ValueError(msg)
        audit = cls(
            id=entry.id,
            action=entry.action.value,
            reason=entry.reason,
            created_at=entry.created_at,
            target_id=str(entry.target.id),
            category=entry.category.value,
        )
        cls._session.add(audit)
        cls._session.commit()
        return audit
