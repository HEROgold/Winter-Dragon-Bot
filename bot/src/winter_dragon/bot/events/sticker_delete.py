"""Monitor and log sticker deletion events in Discord servers.

Track when users delete custom stickers and generate appropriate audit logs.
"""
from typing import override

from discord import Embed
from winter_dragon.bot.events.base.audit_event import AuditEvent


class StickerDelete(AuditEvent):
    """Process sticker deletion events in Discord guilds.

    Monitor the audit log for sticker deletions, log the events,
    and create notification embeds with relevant information.
    """

    @override
    async def handle(self) -> None:
        raise NotImplementedError

    @override
    def create_embed(self) -> Embed:
        raise NotImplementedError
