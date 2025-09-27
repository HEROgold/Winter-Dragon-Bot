"""Module for creating audit events from audit log entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar


if TYPE_CHECKING:
    from discord import AuditLogAction, AuditLogEntry
    from winter_dragon.bot.events.base.audit_event import AuditEvent

class AuditEventFactory:
    """Factory for creating audit events."""

    events: ClassVar[dict[AuditLogAction, type[AuditEvent]]] = {}

    @classmethod
    def register(cls, category: AuditLogAction, event_type: type[AuditEvent]) -> None:
        """Register an audit event class for a category."""
        if category in cls.events:
            return
        cls.events[category] = event_type

    @classmethod
    def get_event(cls, entry: AuditLogEntry) -> AuditEvent:
        """Get the audit event class for a category."""
        if entry.action not in cls.events:
            msg = f"Audit event for {entry.action} not implemented"
            raise NotImplementedError(msg)
        return cls.events[entry.action](entry)
