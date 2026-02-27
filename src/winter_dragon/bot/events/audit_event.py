"""Module for abstracting audit events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, Self, TypeIs

from discord import Embed
from herogold.orm.model import BaseModel

from .factory import AuditEventFactory


if TYPE_CHECKING:
    from discord import AuditLogAction, AuditLogEntry


class AuditLog(BaseModel):
    """Database model for audit logs."""

    action: AuditLogAction
    user_id: int | None
    target_id: int | None
    extra: str | None

    @classmethod
    def from_audit_log(cls, entry: AuditLogEntry) -> AuditLog:
        """Create an audit log from a discord audit log entry."""
        return cls(
            action=entry.action,
            user_id=entry.user.id if entry.user else None,
            target_id=int(entry.target.id) if entry.target and isinstance(entry.target.id, (int, str)) else None,
            extra=str(entry.extra) if entry.extra else None,
        )


class HasMention(Protocol):
    """Protocol for objects that have a mention attribute."""

    mention: str


class AuditEvent(ABC):
    """Base class for audit events."""

    def __init__(self, entry: AuditLogEntry) -> None:
        """Initialize the audit event."""
        super().__init__()
        self.entry = entry

    @property
    def category(self) -> AuditLogAction:
        """Get the log category. lazily evaluated."""
        if not self._category:
            self._category = self.entry.action
        return self._category

    @property
    def db_entry(self) -> AuditLog:
        """Get the database entry. lazily evaluated."""
        if not self._db_entry:
            self._db_entry = AuditLog.from_audit_log(self.entry)  # creates the entry in the database, and returns the entry.
        return self._db_entry

    @abstractmethod
    async def handle(self) -> None:
        """Handle the audit event."""

    def _has_mention(self, obj: object) -> TypeIs[HasMention]:
        """Check if the object has a mention attribute."""
        return hasattr(obj, "mention")

    def create_embed(self) -> Embed:
        """Create an embed for the audit event."""
        if not self._has_mention(self.entry.target):
            msg = "Target does not have a mention attribute."
            raise ValueError(msg)
        target = self.entry.target.mention if hasattr(self.entry.target, "mention") else self.entry.target

        return Embed(
            colour=None,
            color=None,
            title=f"{self.entry.action}",
            type="rich",
            url=None,
            description=f"Performed by {self.entry.user} with target {target}. with extra {self.entry.extra}",
            timestamp=datetime.now(UTC),
        )

    def __init_subclass__(cls: type[Self], action: AuditLogAction) -> None:
        """Register the subclass with the factory."""
        AuditEventFactory.register(action, cls)
