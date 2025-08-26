"""."""
from typing import override

from discord import Embed, Member, User
from discord.audit_logs import _AuditLogProxyMemberMoveOrMessageDelete  # type: ignore[reportPrivateUsage]
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class MemberMove(AuditEvent):
    """Handle member move events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.member_move
        self.logger.debug(f"on member_move: {self.entry.guild=}, {self.entry=}")

    @override
    def create_embed(self) -> Embed:
        user = self.entry.user
        target = self.entry.target
        extra = self.entry.extra
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(target, (User, Member)):
            msg = f"Target is not a discord user: {self.entry.target=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(extra, _AuditLogProxyMemberMoveOrMessageDelete):
            msg = f"Expected extra to be _AuditLogProxyMemberMoveOrMessageDelete, got {type(extra)}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Member Move",
            description=f"{user.mention} moved {target.mention} to {extra.channel} with reason: {self.entry.reason}",
            color=CHANGED_COLOR,
        )
