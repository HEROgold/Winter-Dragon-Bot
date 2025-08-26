"""Monitor and log member prune events in Discord servers.

Track when users prune inactive members and generate appropriate audit logs.
"""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class MemberPrune(AuditEvent):
    """Process member prune events in Discord guilds."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.member_prune
        self.logger.debug(f"on member_prune: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        extra = getattr(self.entry, "extra", {})
        delete_count = getattr(extra, "delete_count", "unknown number of")
        days = getattr(extra, "days", "unknown number of")

        return Embed(
            title="Member Prune",
            description=f"{user.mention} pruned {delete_count} members inactive for {days} days with reason: {self.entry.reason}",  # noqa: E501
            color=DELETED_COLOR,
        )
