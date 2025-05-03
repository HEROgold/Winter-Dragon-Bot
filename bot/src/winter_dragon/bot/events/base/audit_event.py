from abc import ABC, abstractmethod

from discord import AuditLogEntry, Embed
from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.bot.enums.channels import LogCategories


class AuditEvent(ABC, LoggerMixin):
    """Base class for audit events."""

    def __init__(self, entry: AuditLogEntry) -> None:
        """Initialize the audit event."""
        super().__init__()
        self.entry = entry
        self.category = LogCategories.from_AuditLogAction(entry.action)

    @abstractmethod
    async def handle(self) -> None:
        """Handle the audit event."""

    @abstractmethod
    def create_embed(self) -> Embed:
        """Create an embed for the audit event."""
