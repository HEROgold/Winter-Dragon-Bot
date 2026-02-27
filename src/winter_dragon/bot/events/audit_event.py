"""Module for abstracting audit events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import Embed
from winter_dragon.database.tables.audit_log import AuditLog

from .factory import AuditEventFactory


if TYPE_CHECKING:
    from discord import AuditLogAction, AuditLogEntry


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

    def create_embed(self) -> Embed:
        """Create an embed for the audit event."""
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
