"""."""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CREATED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class EmojiCreate(AuditEvent):
    """Handle emoji create events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.emoji_create
        self.logger.debug(f"on emoji_create: {self.entry.guild=}, {self.entry=}")

    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Emoji Create",
            description=f"{user.mention} created emoji {target} with reason: {self.entry.reason}",
            color=CREATED_COLOR,
        )

