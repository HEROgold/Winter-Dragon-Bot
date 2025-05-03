from typing import override

from discord import Embed
from winter_dragon.bot.events.base.audit_event import AuditEvent


class StickerCreate(AuditEvent):
    @override
    async def handle(self) -> None:
        raise NotImplementedError

    @override
    def create_embed(self) -> Embed:
        raise NotImplementedError

