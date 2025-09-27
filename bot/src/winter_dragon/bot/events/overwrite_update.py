"""."""
from typing import override

from discord import AuditLogAction, Embed, Member, Role, User
from discord.abc import GuildChannel
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.events.base.util import add_differences_to_embed
from winter_dragon.bot.settings import Settings


class OverwriteUpdate(AuditEvent, action=AuditLogAction.overwrite_update):
    """Handle permission overwrite update events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.overwrite_update
        self.logger.debug(f"on overwrite_update: {self.entry.guild=}, {self.entry=}")

    @override
    def create_embed(self) -> Embed:
        user = self.entry.user
        channel = self.entry.target
        permissions = self.entry.extra
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(channel, GuildChannel):
            msg = f"Target is not a discord channel: {self.entry.target=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(permissions, (Role, Member)):
            msg = f"Permissions is not a discord role or member: {self.entry.extra=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        properties = (
            "allow",
            "deny",
            "id",
            "type",
        )

        embed = Embed(
            title="Permission Overwrite Created",
            description=(
                f"{user.mention} changed permission overwrite "
                f"for {permissions.mention} in {channel.mention} with reason: {self.entry.reason}"
            ),
            color=Settings.changed_color,
        )
        add_differences_to_embed(embed, self.entry, properties)
        return embed
