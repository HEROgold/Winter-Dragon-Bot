"""Module for handling audit log events."""

from discord import AuditLogEntry
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.events.base.event_handler import AuditEventHandler
from winter_dragon.bot.events.base.factory import AuditEventFactory


class EventListener(Cog):
    """Event listener for audit log entries."""

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the event listener."""
        super().__init__(bot=bot)
        self.bot = bot

    @Cog.listener()
    async def on_audit_log_entry_create(self, entry: AuditLogEntry) -> None:
        """Handle the audit log entry."""
        self.logger.debug(f"Received audit log entry: {entry.id} - {entry.action.name} - {entry.target}")
        audit_event = AuditEventFactory.get_event(entry)
        event_handler = AuditEventHandler(audit_event, self.session)
        await event_handler.handle()


async def setup(bot: WinterDragon) -> None:
    """Load the event listener."""
    await bot.add_cog(EventListener(bot=bot))
