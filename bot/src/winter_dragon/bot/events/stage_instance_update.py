"""Monitor and log stage instance update events in Discord servers.

Track when users modify stage channels and generate appropriate audit logs.
"""
from typing import override

from discord import AuditLogAction, Embed
from winter_dragon.bot.events.base.audit_event import AuditEvent


class StageInstanceUpdate(AuditEvent, action=AuditLogAction.stage_instance_update):
    """Process stage instance update events in Discord guilds.

    Monitor the audit log for stage channel modifications, log the events,
    and create notification embeds with relevant information about changes.
    """

    @override
    async def handle(self) -> None:
        raise NotImplementedError

    @override
    def create_embed(self) -> Embed:
        raise NotImplementedError
