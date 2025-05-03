from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class MemberDisconnect(AuditEvent):
    @override
    async def handle(self) -> None:
        self.logger.debug(f"on member_disconnect: {self.entry.guild=}, {self.entry=}")

    @override
    def create_embed(self) -> Embed:
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            self.logger.warning(f"User is not a discord user: {user=}")
            msg = f"User is not a discord user: {user=}"
            raise TypeError(msg)

        target = self.entry.target
        extra = getattr(self.entry, "extra", None)

        return Embed(
            title="Member Disconnect",
            description=f"{user.mention} disconnected {target} from {extra} with reason: {self.entry.reason}",
            color=DELETED_COLOR,
        )

