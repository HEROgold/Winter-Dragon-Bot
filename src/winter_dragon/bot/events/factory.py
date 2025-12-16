"""Module for creating audit events from audit log entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar


if TYPE_CHECKING:
    from collections.abc import Generator

    from discord import AuditLogAction, AuditLogEntry

    from .audit_event import AuditEvent


class AuditEventFactory:
    """Factory for creating audit events."""

    events: ClassVar[dict[AuditLogAction, list[type[AuditEvent]]]] = {}

    @classmethod
    def register(cls, action: AuditLogAction, event_type: type[AuditEvent]) -> None:
        """Register an audit event class for a category."""
        if action not in cls.events:
            cls.events[action] = [event_type]
            return
        cls.events[action] += [event_type]

    @classmethod
    def get_events(cls, entry: AuditLogEntry) -> Generator[AuditEvent]:
        """Get the audit event class for a category."""
        if entry.action not in cls.events:
            msg = f"Audit event for {entry.action} not implemented"
            raise NotImplementedError(msg)

        for event in cls.events[entry.action]:
            yield event(entry)
