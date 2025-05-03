from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.events.base.util import add_differences_to_embed


class InviteUpdate(AuditEvent):
    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.invite_update
        invite = self.entry.target
        self.logger.debug(f"On invite update: {self.entry.guild=}, {invite=}")


    @override
    def create_embed(self) -> Embed:
        invite = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        properties = (
            "max_age",
            "code",
            "temporary",
            "inviter",
            "channel",
            "uses",
            "max_uses",
        )

        embed = Embed(
            title="Updated Invite",
            description=f"{user.mention} updated invite {invite} with reason: {self.entry.reason}",
            color=CHANGED_COLOR,
        )
        add_differences_to_embed(embed, self.entry, properties)
        return embed

