from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CREATED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class AutomodRuleCreate(AuditEvent):
    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.automod_rule_create
        self.logger.debug(f"on automod_rule_create: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Automod Rule Create",
            description=f"{user.mention} created automod rule {target} with reason: {self.entry.reason}",
            color=CREATED_COLOR,
        )

