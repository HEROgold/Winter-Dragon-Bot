"""Module for handling audit log events."""

from discord import AuditLogEntry
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.events.base.event_handler import AuditEventHandler
from winter_dragon.bot.events.base.factory import AuditEvent_factory


class EventListener(Cog):
    """Event listener for audit log entries."""

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the event listener."""
        super().__init__(bot=bot)
        self.bot = bot

    @Cog.listener()
    async def on_audit_log_entry_create(self, entry: AuditLogEntry) -> None:
        """Handle the audit log entry."""
        self.logger.info(f"Received audit log entry: {entry.id} - {entry.action.name} - {entry.target}")
        event_handler = AuditEventHandler(AuditEvent_factory(entry), self.session)
        await event_handler.handle()


async def setup(bot: WinterDragon) -> None:
    """Load the event listener."""
    await bot.add_cog(EventListener(bot=bot))
