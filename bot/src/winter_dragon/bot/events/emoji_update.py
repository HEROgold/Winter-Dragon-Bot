"""."""
from typing import override

from discord import Embed, Emoji, Member, User
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class EmojiUpdate(AuditEvent):
    """Handle emoji update events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.emoji_update
        self.logger.debug(f"on emoji_update: {self.entry.guild=}, {self.entry=}")
        # TODO: add to DB

    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(target, Emoji):
            msg = f"Target is not a discord emoji: {target=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Emoji Update",
            description=f"{user.mention} updated emoji {target} with reason: {self.entry.reason}",
            color=CHANGED_COLOR,
        )

