from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class IntegrationUpdate(AuditEvent):
    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.integration_update
        self.logger.debug(f"on integration_update: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        # Properties that might be available on integration objects
        target_name = getattr(target, "name", str(target))

        return Embed(
            title="Integration Update",
            description=f"{user.mention} updated integration {target_name} with reason: {self.entry.reason}",
            color=CHANGED_COLOR,
        )

