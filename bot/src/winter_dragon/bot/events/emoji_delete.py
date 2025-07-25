"""."""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class EmojiDelete(AuditEvent):
    """Handle emoji delete events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.emoji_delete
        self.logger.debug(f"on emoji_delete: {self.entry.guild=}, {self.entry=}")

    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Emoji Delete",
            description=f"{user.mention} deleted emoji {target} with reason: {self.entry.reason}",
            color=DELETED_COLOR,
        )

