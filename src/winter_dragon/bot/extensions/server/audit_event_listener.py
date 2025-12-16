"""Module for handling audit log events."""

from discord import AuditLogEntry

from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.events.event_handler import AuditEventHandler
from winter_dragon.bot.events.factory import AuditEventFactory


class EventListener(Cog, auto_load=True):
    """Event listener for audit log entries."""

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the event listener."""
        super().__init__(bot=bot)

    @Cog.listener()
    async def on_audit_log_entry_create(self, entry: AuditLogEntry) -> None:
        """Handle the audit log entry."""
        self.logger.debug(f"Received audit log entry: {entry.id} - {entry.action.name} - {entry.target}")
        for audit_event in AuditEventFactory.get_events(entry):
            event_handler = AuditEventHandler(audit_event, self.session)
            await event_handler.handle()
