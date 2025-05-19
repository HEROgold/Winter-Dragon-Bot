"""Monitor and log sticker creation events in Discord servers.

Track when users create new custom stickers and generate appropriate audit logs.
"""
from typing import override

from discord import Embed
from winter_dragon.bot.events.base.audit_event import AuditEvent


class StickerCreate(AuditEvent):
    """Process sticker creation events in Discord guilds.

    Monitor the audit log for sticker creations, log the events,
    and create notification embeds with relevant information.
    """

    @override
    async def handle(self) -> None:
        raise NotImplementedError

    @override
    def create_embed(self) -> Embed:
        raise NotImplementedError

