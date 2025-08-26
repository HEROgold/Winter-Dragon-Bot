"""."""
from typing import override

from discord import Embed, Member, User
from discord.abc import GuildChannel
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class ChannelDelete(AuditEvent):
    """Handle channel delete events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.channel_delete
        self.logger.debug(f"On channel delete: {self.entry.guild=}, {self.entry.target=}")

    @override
    def create_embed(self) -> Embed:
        channel = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(channel, GuildChannel):
            msg = f"Target is not a discord channel: {channel=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        category = f"from {channel.category.mention}" if channel.category else ""
        return Embed(
            title="Channel Deleted",
            description=(
                f"{user.mention} deleted {channel.mention} {channel.name}{category}"
                f"with reason: {self.entry.reason}"
            ),
            color=DELETED_COLOR,
        )
