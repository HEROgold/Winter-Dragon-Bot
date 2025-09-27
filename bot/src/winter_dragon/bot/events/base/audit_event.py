"""Module for abstracting audit events."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.bot.enums.channels import LogCategories
from winter_dragon.bot.events.base.factory import AuditEventFactory
from winter_dragon.database.tables.audit_log import AuditLog


if TYPE_CHECKING:
    from discord import AuditLogAction, AuditLogEntry, Embed


# This system is limited, to only one handler per event type.
# It's possible we want multiple handler for a single event type, with different "filters"
# we should design for that eventuality.
# e.g. log channel create events log to different channels based on channel type.
class AuditEvent(ABC, LoggerMixin):
    """Base class for audit events."""

    def __init__(self, entry: AuditLogEntry) -> None:
        """Initialize the audit event."""
        super().__init__()
        self.entry = entry

    @property
    def category(self) -> LogCategories:
        """Get the log category. lazily evaluated."""
        if not self._category:
            self._category = LogCategories.from_AuditLogAction(self.entry.action)
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

    def __init_subclass__(cls: type[AuditEvent], action: AuditLogAction) -> None:
        """Register the subclass with the factory."""
        AuditEventFactory.register(action, cls)
