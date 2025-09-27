"""."""
from typing import override

from discord import AuditLogAction, Embed, Member, User
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class GuildUpdate(AuditEvent, action=AuditLogAction.guild_update):
    """Handle guild update events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.guild_update
        self.logger.debug(f"On guild update: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Guild Updated",
            description=f"{user.mention} updated guild settings with reason: {self.entry.reason}",
            color=Settings.changed_color,
        )
