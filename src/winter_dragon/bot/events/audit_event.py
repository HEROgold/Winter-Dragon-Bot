"""Module for abstracting audit events."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.bot.events.base.factory import AuditEventFactory
from winter_dragon.database.tables.audit_log import AuditLog


if TYPE_CHECKING:
    from discord import AuditLogAction, AuditLogEntry, Embed


class AuditEvent(ABC, LoggerMixin):
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
            self._db_entry = AuditLog.from_audit_log(self.entry) # creates the entry in the database, and returns the entry.
        return self._db_entry

    @abstractmethod
    async def handle(self) -> None:
        """Handle the audit event."""

    @abstractmethod
    def create_embed(self) -> Embed:
        """Create an embed for the audit event."""

    def __init_subclass__(cls: type[Self], action: AuditLogAction) -> None:
        """Register the subclass with the factory."""
        AuditEventFactory.register(action, cls)
