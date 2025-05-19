"""Monitor and log sticker update events in Discord servers.

Track when users modify custom stickers and generate appropriate audit logs.
"""
from typing import override

from discord import Embed
from winter_dragon.bot.events.base.audit_event import AuditEvent


class StickerUpdate(AuditEvent):
    """Process sticker update events in Discord guilds.

    Monitor the audit log for sticker modifications, log the events,
    and create notification embeds with relevant information about changes.
    """

    @override
    async def handle(self) -> None:
        raise NotImplementedError

    @override
    def create_embed(self) -> Embed:
        raise NotImplementedError

