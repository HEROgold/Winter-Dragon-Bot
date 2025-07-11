"""Module for handling app command permission updates."""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class AppCommandPermissionUpdate(AuditEvent):
    """Handle app command permission updates."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.app_command_permission_update
        self.logger.debug(f"on app_command_permission_update: {self.entry.guild=}, {self.entry=}")

    @override
    def create_embed(self) -> Embed:
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="App Command Permission Update",
            description=f"{user.mention} updated app command permissions with reason: {self.entry.reason}",
            color=CHANGED_COLOR,
        )
