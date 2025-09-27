"""."""
from typing import override

from discord import AuditLogAction, Embed
from winter_dragon.bot.events.base.audit_event import AuditEvent


class StageInstanceCreate(AuditEvent, action=AuditLogAction.stage_instance_create):
    """Handle stage instance create events."""

    @override
    async def handle(self) -> None:
        raise NotImplementedError

    @override
    def create_embed(self) -> Embed:
        raise NotImplementedError
