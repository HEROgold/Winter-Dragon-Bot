"""."""

from typing import override

from discord import Embed, Member, User
from discord.abc import GuildChannel
from discord.audit_logs import _AuditLogProxyMessageBulkDelete  # type: ignore[reportPrivateUsage]
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class MessageBulkDelete(AuditEvent):
    """Handle message bulk delete events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.message_bulk_delete
        self.logger.debug(f"on message_bulk_delete: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:  # sourcery skip: extract-duplicate-method
        channel = self.entry.target
        user = self.entry.user
        extra = self.entry.extra
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(channel, GuildChannel):
            msg = f"Channel is not a GuildChannel: {type(channel)}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(self.entry.extra, _AuditLogProxyMessageBulkDelete):
            msg = f"Expected extra to be _AuditLogProxyMemberMoveOrMessageDelete, got {extra=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        count = self.entry.extra.count

        return Embed(
            title="Bulk Message Delete",
            description=f"{user.mention} bulk deleted {count} messages in {channel.mention} with reason: {self.entry.reason}",
            color=DELETED_COLOR,
        )

