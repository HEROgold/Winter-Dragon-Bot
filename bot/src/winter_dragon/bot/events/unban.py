"""Module containing Unban event handling.

This module provides functionality for monitoring and logging when users are unbanned from a Discord server.
"""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CREATED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class Unban(AuditEvent):
    """Handles the unban event.

    This class processes Discord unban events, generating logs and notifications
    when a user's ban is removed from a guild.
    """

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.unban
        self.logger.debug(f"on unban: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        target_type = getattr(target, "type", "")

        return Embed(
            title="Unban",
            description=f"{user.mention} unbanned {target_type} {target} with reason: {self.entry.reason}",
            color=CREATED_COLOR,
        )

